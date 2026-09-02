from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.v1_read_service import V1ReadService


def _session_with_results():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    home = Team(name="Home Team", league="NFL", sport="NFL")
    away = Team(name="Away Team", league="NFL", sport="NFL")
    db.add_all([home, away])
    db.flush()

    game = Game(
        sport="NFL",
        league="NFL",
        game_date=now - timedelta(days=1),
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=24,
        away_score=17,
        status="final",
    )
    db.add(game)
    db.flush()

    result_specs = (
        ("spread", "HOME", 160.0, 85.0, -110, "WIN", 150.0, now),
        ("moneyline", "AWAY", 140.0, 75.0, 150, "LOSS", -100.0, now),
        ("total", "OVER", 120.0, 65.0, -110, "PUSH", 0.0, now),
        (
            "spread",
            "HOME",
            110.0,
            55.0,
            -110,
            "WIN",
            100.0,
            now - timedelta(days=8),
        ),
    )
    for market, selection, npi, confidence, odds, outcome, profit_loss, created_at in result_specs:
        prediction = Prediction(
            game_id=game.id,
            market=market,
            selection=selection,
            line_value=-3.5,
            american_odds=odds,
            npi_score=npi,
            confidence_score=confidence,
            model_version="NPI-4.0",
        )
        db.add(prediction)
        db.flush()
        db.add(
            PredictionResult(
                prediction_id=prediction.id,
                actual_result="HOME",
                predicted_result=selection,
                outcome=outcome,
                profit_loss=profit_loss,
                created_at=created_at,
            )
        )

    db.commit()
    return db


def test_performance_intelligence_default_returns_all_sections():
    db = _session_with_results()
    try:
        data = V1ReadService().get_performance_intelligence(db)
    finally:
        db.close()

    assert data["period_days"] == 30
    assert {
        "overall",
        "by_market",
        "by_sport",
        "by_npi_band",
        "by_confidence_band",
        "by_odds_band",
        "by_side_type",
        "by_model_version",
    }.issubset(data)


def test_performance_intelligence_seven_days_filters_older_results():
    db = _session_with_results()
    try:
        data = V1ReadService().get_performance_intelligence(db, days=7)
    finally:
        db.close()

    assert data["period_days"] == 7
    assert data["overall"]["total_bets"] == 3


def test_performance_intelligence_push_is_excluded_from_win_rate():
    db = _session_with_results()
    try:
        overall = V1ReadService().get_performance_intelligence(
            db,
            days=7,
        )["overall"]
    finally:
        db.close()

    assert overall["wins"] == 1
    assert overall["losses"] == 1
    assert overall["pushes"] == 1
    assert overall["win_rate"] == 50.0


def test_performance_intelligence_converts_profit_loss_to_units():
    db = _session_with_results()
    try:
        overall = V1ReadService().get_performance_intelligence(
            db,
            days=7,
        )["overall"]
    finally:
        db.close()

    assert overall["units_won"] == 0.5