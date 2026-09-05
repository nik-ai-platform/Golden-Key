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


def _session_with_npi_4_spread_results():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    home = Team(name="Calibration Home", league="NFL", sport="NFL")
    away = Team(name="Calibration Away", league="NFL", sport="NFL")
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport="NFL",
        league="NFL",
        game_date=now - timedelta(days=1),
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=24,
        away_score=20,
        status="final",
    )
    db.add(game)
    db.flush()

    specs = (
        ("spread", "HOME", "NPI-4.0", 160, 85, 12, 62, "WIN", 100, 0),
        ("spread", "AWAY", "NPI-4.0", 140, 75, -15, 35, "LOSS", -100, 0),
        ("spread", "HOME", "NPI-4.0", 180, 92, 22, 72, "PUSH", 0, 0),
        ("spread", "HOME", "NPI-4.0", 110, 55, 6, 54, "WIN", 100, 8),
        ("spread", "AWAY", "NPI-4.0", 90, 65, -8, 42, "LOSS", -100, 45),
        ("spread", "PASS", "NPI-4.0", 130, 65, 5, 55, "PUSH", 0, 0),
        ("moneyline", "HOME", "NPI-4.0", 130, 65, 10, 60, "WIN", 100, 0),
        ("spread", "HOME", "NPI-3.0", 130, 65, 10, 60, "WIN", 100, 0),
    )
    for market, selection, version, npi, confidence, edge, probability, outcome, profit, age in specs:
        prediction = Prediction(
            game_id=game.id,
            market=market,
            selection=selection,
            line_value=-3.5,
            american_odds=-110,
            npi_score=npi,
            confidence_score=confidence,
            projected_edge=edge,
            simulation_probability=probability,
            model_version=version,
        )
        db.add(prediction)
        db.flush()
        db.add(
            PredictionResult(
                prediction_id=prediction.id,
                actual_result="24-20",
                predicted_result=selection,
                outcome=outcome,
                profit_loss=profit,
                created_at=now - timedelta(days=age),
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


def test_npi_4_spread_summary_filters_market_version_pass_and_period():
    db = _session_with_npi_4_spread_results()
    try:
        seven_day = V1ReadService().get_performance_intelligence(db, days=7)["npi_4_spread"]
        thirty_day = V1ReadService().get_performance_intelligence(db, days=30)["npi_4_spread"]
        ninety_day = V1ReadService().get_performance_intelligence(db, days=90)["npi_4_spread"]
    finally:
        db.close()

    assert seven_day["summary"] == {
        "sample_size": 3,
        "wins": 1,
        "losses": 1,
        "pushes": 1,
        "win_rate": 50.0,
        "units": 0.0,
        "roi": 0.0,
    }
    assert thirty_day["summary"]["sample_size"] == 4
    assert thirty_day["summary"]["units"] == 1.0
    assert thirty_day["summary"]["roi"] == 25.0
    assert ninety_day["summary"]["sample_size"] == 5


def test_npi_4_spread_returns_fixed_npi_confidence_and_absolute_edge_bands():
    db = _session_with_npi_4_spread_results()
    try:
        spread = V1ReadService().get_performance_intelligence(db, days=7)["npi_4_spread"]
    finally:
        db.close()

    npi = {row["key"]: row for row in spread["npi_bands"]}
    confidence = {row["key"]: row for row in spread["confidence_bands"]}
    edge = {row["key"]: row for row in spread["projected_edge_bands"]}

    assert list(npi) == ["0-99", "100-124", "125-149", "150-174", "175-200"]
    assert npi["0-99"]["sample_size"] == 0
    assert npi["125-149"]["losses"] == 1
    assert npi["150-174"]["wins"] == 1
    assert npi["175-200"]["pushes"] == 1
    assert confidence["70-79"]["losses"] == 1
    assert confidence["80-89"]["wins"] == 1
    assert confidence["90-100"]["pushes"] == 1
    assert edge["10-14.9"]["wins"] == 1
    assert edge["15-19.9"]["losses"] == 1
    assert edge["20+"]["pushes"] == 1


def test_npi_4_spread_normalizes_away_probability_and_calculates_brier():
    db = _session_with_npi_4_spread_results()
    try:
        spread = V1ReadService().get_performance_intelligence(db, days=7)["npi_4_spread"]
    finally:
        db.close()

    calibration = {row["key"]: row for row in spread["probability_calibration"]}
    assert list(calibration) == ["50-54.9", "55-59.9", "60-64.9", "65-69.9", "70+"]
    assert calibration["50-54.9"]["sample_size"] == 0
    assert calibration["60-64.9"] == {
        "key": "60-64.9",
        "sample_size": 1,
        "wins": 1,
        "losses": 0,
        "pushes": 0,
        "predicted_probability_average": 62.0,
        "actual_win_rate": 100.0,
    }
    assert calibration["65-69.9"]["predicted_probability_average"] == 65.0
    assert calibration["65-69.9"]["losses"] == 1
    assert calibration["70+"]["pushes"] == 1
    assert spread["brier_sample_size"] == 2
    assert spread["brier_score"] == 0.2835