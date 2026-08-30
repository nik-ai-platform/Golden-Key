from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.odds import Odds  # noqa: F401
from app.models.prediction_record import Prediction
from app.models.team import Team  # noqa: F401
from app.services.live_data_service import LiveDataService
from app.services.npi_engine import NPIEngine
from app.services.prediction_engine import PredictionEngine
from app.workers.game_importer import GameOddsImporter


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _event(with_odds=False):
    event = {
        "id": "ncaaf-provider-game-1",
        "home_team": "Texas Longhorns",
        "away_team": "Ohio State Buckeyes",
        "commence_time": "2026-09-05T19:30:00Z",
        "bookmakers": [],
    }
    if with_odds:
        event["bookmakers"] = [
            {
                "title": "Test Sportsbook",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": event["home_team"], "price": -280},
                            {"name": event["away_team"], "price": 230},
                        ],
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": event["home_team"], "point": -7.5},
                            {"name": event["away_team"], "point": 7.5},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 52.5},
                            {"name": "Under", "point": 52.5},
                        ],
                    },
                ],
            }
        ]
    return event


def _odds():
    return SimpleNamespace(
        spread_home=-7.5,
        spread_away=7.5,
        moneyline_home=-280,
        moneyline_away=230,
        total=52.5,
    )


def test_live_data_maps_ncaaf_to_provider_identifier(monkeypatch):
    response = MagicMock()
    response.json.return_value = []
    request = MagicMock(return_value=response)
    monkeypatch.setattr("app.services.live_data_service.requests.get", request)

    LiveDataService().fetch_games("NCAAF")

    assert request.call_args.args[0].endswith(
        "/americanfootball_ncaaf/odds"
    )


def test_live_data_preserves_existing_provider_identifier(monkeypatch):
    response = MagicMock()
    response.json.return_value = []
    request = MagicMock(return_value=response)
    monkeypatch.setattr("app.services.live_data_service.requests.get", request)

    LiveDataService().fetch_games("baseball_mlb")

    assert request.call_args.args[0].endswith("/baseball_mlb/odds")


def test_ncaaf_import_is_idempotent_by_provider_game_id():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event()]
    importer = GameOddsImporter(db=db, live_data_service=live_data)

    first = importer.import_games("NCAAF")
    second = importer.import_games("NCAAF")

    games = db.query(Game).all()
    assert len(games) == 1
    assert first[0].id == second[0].id == games[0].id
    assert games[0].provider_game_id == "ncaaf-provider-game-1"
    assert games[0].sport == "NCAAF"


def test_ncaaf_uses_default_npi_profile_and_stays_on_200_point_scale(
    monkeypatch,
):
    def missing_profile(db, sport, model_version):
        raise ValueError(
            "No NPI weight profile found for NCAAF NPI-4.0"
        )

    monkeypatch.setattr(
        NPIEngine.weight_profiles,
        "get_profile",
        missing_profile,
    )

    result = NPIEngine().calculate(
        db=object(),
        game=SimpleNamespace(),
        odds=_odds(),
        sport="NCAAF",
        model_version="NPI-4.0",
    )

    assert 0 <= result["npi_score"] <= 200
    assert [factor["weight"] for factor in result["factors"]] == list(
        NPIEngine.DEFAULT_WEIGHTS.values()
    )


def test_ncaaf_builds_unified_spread_moneyline_and_total_predictions():
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.side_effect = [
        {
            "win_probability": 62,
            "runs": 10000,
            "average_margin": 4.0,
        },
        {
            "win_probability": 58,
            "runs": 10000,
            "average_margin": 2.0,
        },
    ]

    specifications = engine._market_specifications(
        sport="NCAAF",
        odds=_odds(),
        spread_npi={"npi_score": 110, "factors": []},
    )

    assert [item["market"] for item in specifications] == [
        "spread",
        "moneyline",
        "total",
    ]
    assert all(0 <= item["npi_score"] <= 200 for item in specifications)
    assert specifications[0]["line_value"] is not None
    assert specifications[1]["american_odds"] is not None
    assert specifications[2]["line_value"] == 52.5


def test_one_ncaaf_event_persists_complete_odds_and_three_predictions():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event(with_odds=True)]
    game = GameOddsImporter(
        db=db,
        live_data_service=live_data,
    ).import_games("NCAAF")[0]
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="Incomplete Sportsbook",
            spread_home=-7.0,
            spread_away=7.0,
            moneyline_home=None,
            moneyline_away=None,
            total=53.0,
        )
    )
    db.commit()

    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: NCAAF"
    )
    engine.ai_engine = MagicMock()
    engine.ai_engine.generate_analysis.return_value = {
        "engine_version": "test",
        "summary": "NCAAF test analysis",
        "explanation": "NCAAF test analysis",
    }

    predictions = engine.analyze_markets(
        db=db,
        game_id=game.id,
        persist=True,
    )

    stored_game = db.query(Game).filter(Game.id == game.id).one()
    stored_odds = (
        db.query(Odds)
        .filter(
            Odds.game_id == game.id,
            Odds.spread_home.is_not(None),
            Odds.spread_away.is_not(None),
            Odds.moneyline_home.is_not(None),
            Odds.moneyline_away.is_not(None),
            Odds.total.is_not(None),
        )
        .one()
    )
    stored_predictions = (
        db.query(Prediction)
        .filter(Prediction.game_id == game.id)
        .all()
    )
    assert stored_game.provider_game_id == "ncaaf-provider-game-1"
    assert stored_game.sport == "NCAAF"
    assert (
        stored_odds.spread_home,
        stored_odds.spread_away,
        stored_odds.moneyline_home,
        stored_odds.moneyline_away,
        stored_odds.total,
    ) == (-7.5, 7.5, -280, 230, 52.5)
    assert [prediction.market for prediction in predictions] == [
        "spread",
        "moneyline",
        "total",
    ]
    assert len(stored_predictions) == 3
    assert all(0 <= prediction.npi_score <= 200 for prediction in predictions)