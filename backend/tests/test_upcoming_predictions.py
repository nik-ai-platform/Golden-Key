from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.odds import Odds  # noqa: F401
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult  # noqa: F401
from app.models.team import Team
from app.models.user import User  # noqa: F401
from app.models.user_prediction import UserPrediction  # noqa: F401
from app.services.v1_read_service import V1ReadService


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _add_game(db, *, kickoff, sport="NFL", status="scheduled", selection="HOME"):
    suffix = db.query(Game).count()
    home = Team(name=f"Home {suffix}", league=sport, sport=sport)
    away = Team(name=f"Away {suffix}", league=sport, sport=sport)
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport=sport,
        league=sport,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff,
        status=status,
    )
    db.add(game)
    db.flush()
    prediction = Prediction(
        game_id=game.id,
        model_version="NPI-4.0",
        market="spread",
        selection=selection,
        line_value=-3.5,
        american_odds=-110,
        npi_score=170,
        confidence_score=82,
        simulation_probability=61,
        projected_edge=5,
    )
    db.add(prediction)
    db.commit()
    return game, prediction


def test_upcoming_predictions_returns_the_full_fourteen_day_window():
    db = _session()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today, _ = _add_game(db, kickoff=now + timedelta(hours=1))
    tomorrow, _ = _add_game(db, kickoff=now + timedelta(days=1))
    horizon, _ = _add_game(db, kickoff=now + timedelta(days=13, hours=23))
    _add_game(db, kickoff=now + timedelta(days=14, minutes=1))
    _add_game(db, kickoff=now - timedelta(minutes=1))
    _add_game(db, kickoff=now + timedelta(days=2), status="final")
    _add_game(db, kickoff=now + timedelta(days=3), status="live")

    feed = V1ReadService().get_upcoming_predictions(db=db)

    assert {item["game_id"] for item in feed["predictions"]} == {
        today.id,
        tomorrow.id,
        horizon.id,
    }
    assert feed["count"] == 3
    assert datetime.fromisoformat(feed["end_date"].replace("Z", "+00:00")) - datetime.fromisoformat(
        feed["start_date"].replace("Z", "+00:00")
    ) == timedelta(days=14)


def test_upcoming_predictions_preserves_sport_and_pass_filters():
    db = _session()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    nfl_game, _ = _add_game(db, kickoff=now + timedelta(hours=1))
    ncaaf_game, _ = _add_game(
        db,
        kickoff=now + timedelta(hours=2),
        sport="NCAAF",
    )
    pass_game, _ = _add_game(
        db,
        kickoff=now + timedelta(hours=3),
        selection="PASS",
    )

    nfl_feed = V1ReadService().get_upcoming_predictions(db=db, sport="nfl")
    with_passes = V1ReadService().get_upcoming_predictions(
        db=db,
        sport="NFL",
        include_passes=True,
    )

    assert nfl_feed["sport"] == "NFL"
    assert {item["game_id"] for item in nfl_feed["predictions"]} == {nfl_game.id}
    assert {item["game_id"] for item in with_passes["predictions"]} == {
        nfl_game.id,
        pass_game.id,
    }
    assert ncaaf_game.id not in {
        item["game_id"] for item in with_passes["predictions"]
    }