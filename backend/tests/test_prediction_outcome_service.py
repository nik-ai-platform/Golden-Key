from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models import team  # noqa: F401
from app.models import game  # noqa: F401
from app.models import nik_score  # noqa: F401
from app.models import prediction_outcome  # noqa: F401
from app.models.game import Game
from app.models.nik_score import NikScore
from app.models.prediction_outcome import PredictionOutcome
from app.models.team import Team
from app.services.prediction_outcome_service import PredictionOutcomeService



def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()



def _seed_game(
    session,
    *,
    home_score,
    away_score,
    recommendation,
    confidence,
    predicted_home_score,
    predicted_away_score,
    winner_team_id=None,
):
    home_team = Team(name="Home Team", league="NBA", sport="basketball")
    away_team = Team(name="Away Team", league="NBA", sport="basketball")
    session.add_all([home_team, away_team])
    session.flush()

    game = Game(
        sport="basketball",
        league="NBA",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        game_date=datetime(2026, 1, 1, 12, 0, 0),
        home_score=home_score,
        away_score=away_score,
        winner_team_id=winner_team_id,
    )
    session.add(game)
    session.flush()

    prediction = NikScore(
        game_id=game.id,
        home_score=predicted_home_score,
        away_score=predicted_away_score,
        confidence=confidence,
        recommendation=recommendation,
    )
    session.add(prediction)
    session.commit()

    return session, game, prediction, home_team, away_team



def test_evaluate_prediction_marks_correct_when_winner_matches():
    session = _build_session()
    session, game, prediction, home_team, _away_team = _seed_game(
        session,
        home_score=108,
        away_score=102,
        recommendation="Home Team",
        confidence=92.0,
        predicted_home_score=110,
        predicted_away_score=104,
    )

    game.winner_team_id = home_team.id
    session.commit()

    service = PredictionOutcomeService()
    outcome = service.evaluate_prediction(session, prediction.id)

    assert outcome is not None
    assert outcome.prediction_correct is True
    assert outcome.predicted_winner == "Home Team"
    assert outcome.actual_winner == "Home Team"
    assert outcome.predicted_confidence == 92.0
    assert outcome.point_spread_error == 0.0
    assert session.query(PredictionOutcome).count() == 1



def test_evaluate_prediction_marks_incorrect_when_winner_differs():
    session = _build_session()
    session, _game, prediction, home_team, away_team = _seed_game(
        session,
        home_score=100,
        away_score=96,
        recommendation="Home Team",
        confidence=35.0,
        predicted_home_score=120,
        predicted_away_score=110,
    )

    game = session.query(Game).filter(Game.id == prediction.game_id).first()
    game.winner_team_id = away_team.id
    session.commit()

    service = PredictionOutcomeService()
    outcome = service.evaluate_prediction(session, prediction.id)

    assert outcome is not None
    assert outcome.prediction_correct is False
    assert outcome.predicted_winner == "Home Team"
    assert outcome.actual_winner == "Away Team"
    assert outcome.predicted_confidence == 35.0
    assert outcome.point_spread_error == 6.0



def test_evaluate_prediction_returns_none_when_game_missing_result():
    session = _build_session()
    session, _game, prediction, _home_team, _away_team = _seed_game(
        session,
        home_score=None,
        away_score=None,
        winner_team_id=None,
        recommendation="Home Team",
        confidence=72.0,
        predicted_home_score=105,
        predicted_away_score=101,
    )

    service = PredictionOutcomeService()
    outcome = service.evaluate_prediction(session, prediction.id)

    assert outcome is None
    assert session.query(PredictionOutcome).count() == 0



def test_evaluate_prediction_prevents_duplicates():
    session = _build_session()
    session, _game, prediction, home_team, _away_team = _seed_game(
        session,
        home_score=111,
        away_score=104,
        recommendation="Home Team",
        confidence=88.0,
        predicted_home_score=113,
        predicted_away_score=105,
    )

    game = session.query(Game).filter(Game.id == prediction.game_id).first()
    game.winner_team_id = home_team.id
    session.commit()

    service = PredictionOutcomeService()
    first = service.evaluate_prediction(session, prediction.id)
    second = service.evaluate_prediction(session, prediction.id)

    assert first.id == second.id
    assert session.query(PredictionOutcome).count() == 1



def test_evaluate_completed_games_updates_metrics():
    session = _build_session()

    home_team_a = Team(name="Home A", league="NBA", sport="basketball")
    away_team_a = Team(name="Away A", league="NBA", sport="basketball")
    home_team_b = Team(name="Home B", league="NBA", sport="basketball")
    away_team_b = Team(name="Away B", league="NBA", sport="basketball")
    session.add_all([home_team_a, away_team_a, home_team_b, away_team_b])
    session.flush()

    game_one = Game(
        sport="basketball",
        league="NBA",
        home_team_id=home_team_a.id,
        away_team_id=away_team_a.id,
        game_date=datetime(2026, 1, 1, 12, 0, 0),
        home_score=108,
        away_score=102,
        winner_team_id=home_team_a.id,
    )
    game_two = Game(
        sport="basketball",
        league="NBA",
        home_team_id=home_team_b.id,
        away_team_id=away_team_b.id,
        game_date=datetime(2026, 1, 2, 12, 0, 0),
        home_score=100,
        away_score=96,
        winner_team_id=away_team_b.id,
    )
    session.add_all([game_one, game_two])
    session.flush()

    session.add_all(
        [
            NikScore(
                game_id=game_one.id,
                home_score=110,
                away_score=104,
                confidence=92.0,
                recommendation="Home A",
            ),
            NikScore(
                game_id=game_two.id,
                home_score=120,
                away_score=110,
                confidence=35.0,
                recommendation="Home B",
            ),
        ]
    )
    session.commit()

    service = PredictionOutcomeService()
    outcomes = service.evaluate_completed_games(session)
    metrics = service.update_prediction_metrics(session)

    assert len(outcomes) == 2
    assert metrics["winner_accuracy"] == 50.0
    assert metrics["confidence_accuracy"] == 78.5
    assert metrics["margin_error"] == 3.0
    assert metrics["total_outcomes"] == 2
