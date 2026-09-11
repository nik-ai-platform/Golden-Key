from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.analytics.ncaaf_rule_registry import (
    NCAAF_ATS_RULES,
    match_ncaaf_ats_rule,
)
from app.database.base import Base
from app.models.game import Game
from app.models.ncaaf_rule_intelligence import NcaafRuleIntelligence
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.ncaaf_rule_intelligence_service import (
    record_rule_intelligence_for_prediction,
    settle_rule_intelligence_for_prediction,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _prediction_fixture(
    db: Session,
    *,
    sport: str = "NCAAF",
    market: str = "spread",
    model_version: str = "NPI-4.0",
    selection: str = "AWAY",
    spread_home: float = 2.5,
    spread_away: float = -2.5,
) -> tuple[Prediction, Odds, Game]:
    home = Team(name="Home", sport=sport, league=sport)
    away = Team(name="Away", sport=sport, league=sport)
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport=sport,
        league=sport,
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime(2026, 9, 12, tzinfo=UTC),
    )
    db.add(game)
    db.flush()
    odds = Odds(
        game_id=game.id,
        sportsbook="Test",
        spread_home=spread_home,
        spread_away=spread_away,
    )
    db.add(odds)
    db.flush()
    prediction = Prediction(
        game_id=game.id,
        model_version=model_version,
        market=market,
        selection=selection,
        line_value=spread_away if selection == "AWAY" else spread_home,
        odds_snapshot_id=odds.id,
        npi_score=100,
        confidence_score=72.5,
        simulation_probability=61.0,
        projected_edge=11.0,
    )
    db.add(prediction)
    db.flush()
    return prediction, odds, game


def test_registry_contains_exactly_18_rules():
    assert len(NCAAF_ATS_RULES) == 18


def test_away_negative_2_5_matches():
    rule = match_ncaaf_ats_rule(spread_home=2.5, spread_away=-2.5)

    assert rule is not None
    assert rule.code == "AWAY_NEG_2_5_COVERS"
    assert rule.pick_side == "AWAY"


def test_away_negative_3_does_not_match():
    assert match_ncaaf_ats_rule(spread_home=3.0, spread_away=-3.0) is None


def test_home_negative_6_5_matches():
    rule = match_ncaaf_ats_rule(spread_home=-6.5, spread_away=6.5)

    assert rule is not None
    assert rule.code == "HOME_NEG_6_5_COVERS"
    assert rule.pick_side == "HOME"


def test_home_negative_7_favors_away():
    rule = match_ncaaf_ats_rule(spread_home=-7.0, spread_away=7.0)

    assert rule is not None
    assert rule.code == "HOME_NEG_7_DOES_NOT_COVER"
    assert rule.pick_side == "AWAY"


def test_away_negative_3_5_favors_home():
    rule = match_ncaaf_ats_rule(spread_home=3.5, spread_away=-3.5)

    assert rule is not None
    assert rule.code == "AWAY_NEG_3_5_DOES_NOT_COVER"
    assert rule.pick_side == "HOME"


@pytest.mark.parametrize(
    ("selection", "expected_comparison"),
    [("AWAY", "AGREE"), ("HOME", "DISAGREE"), ("PASS", "NPI_PASS")],
)
def test_matching_prediction_creates_expected_comparison(
    db,
    selection,
    expected_comparison,
):
    prediction, odds, _ = _prediction_fixture(db, selection=selection)

    record = record_rule_intelligence_for_prediction(db, prediction, odds)

    assert record is not None
    assert record.rule_code == "AWAY_NEG_2_5_COVERS"
    assert record.rule_pick_side == "AWAY"
    assert record.rule_pick_line == -2.5
    assert record.comparison == expected_comparison
    assert db.query(NcaafRuleIntelligence).count() == 1


def test_recording_same_prediction_twice_is_idempotent(db):
    prediction, odds, _ = _prediction_fixture(db)

    first = record_rule_intelligence_for_prediction(db, prediction, odds)
    second = record_rule_intelligence_for_prediction(db, prediction, odds)

    assert first is second
    assert db.query(NcaafRuleIntelligence).count() == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"sport": "NFL"},
        {"market": "moneyline"},
        {"model_version": "NPI-3.0"},
        {"spread_home": 3.0, "spread_away": -3.0},
    ],
)
def test_ineligible_prediction_does_not_create_record(db, overrides):
    prediction, odds, _ = _prediction_fixture(db, **overrides)

    assert record_rule_intelligence_for_prediction(db, prediction, odds) is None
    assert db.query(NcaafRuleIntelligence).count() == 0


@pytest.mark.parametrize(
    ("rule_pick_side", "rule_pick_line", "scores", "expected"),
    [
        ("HOME", -6.5, (31, 20), "WIN"),
        ("AWAY", -2.5, (20, 28), "WIN"),
        ("HOME", -6.5, (24, 21), "LOSS"),
        ("AWAY", -2.5, (21, 23.5), "PUSH"),
    ],
)
def test_settlement_grades_stored_rule_pick(
    db,
    rule_pick_side,
    rule_pick_line,
    scores,
    expected,
):
    prediction, odds, game = _prediction_fixture(db)
    record = record_rule_intelligence_for_prediction(db, prediction, odds)
    assert record is not None
    record.rule_pick_side = rule_pick_side
    record.rule_pick_line = rule_pick_line
    game.home_score, game.away_score = scores
    result = PredictionResult(
        prediction_id=prediction.id,
        actual_result="final",
        predicted_result="selection",
        outcome="LOSS",
        created_at=datetime(2026, 9, 13, tzinfo=UTC),
    )
    db.add(result)
    db.flush()

    settled = settle_rule_intelligence_for_prediction(db, result, game)

    assert settled is record
    assert record.rule_result == expected
    assert record.npi_result == "LOSS"
    assert record.settled_at == result.created_at


def test_npi_pass_keeps_result_null_and_rerun_is_idempotent(db):
    prediction, odds, game = _prediction_fixture(db, selection="PASS")
    record = record_rule_intelligence_for_prediction(db, prediction, odds)
    assert record is not None
    game.home_score = 20
    game.away_score = 24
    result = PredictionResult(
        prediction_id=prediction.id,
        actual_result="NO_BET",
        predicted_result="PASS",
        outcome="PUSH",
        created_at=datetime(2026, 9, 13, tzinfo=UTC),
    )
    db.add(result)
    db.flush()

    first = settle_rule_intelligence_for_prediction(db, result, game)
    first_values = (record.rule_result, record.npi_result, record.settled_at)
    second = settle_rule_intelligence_for_prediction(db, result, game)

    assert first is second is record
    assert record.npi_result is None
    assert (record.rule_result, record.npi_result, record.settled_at) == first_values


def test_tracker_does_not_mutate_prediction_decision_fields(db):
    prediction, odds, _ = _prediction_fixture(db, selection="HOME")
    before = (
        prediction.selection,
        prediction.confidence_score,
        prediction.simulation_probability,
        prediction.projected_edge,
        prediction.odds_snapshot_id,
    )

    record_rule_intelligence_for_prediction(db, prediction, odds)

    assert (
        prediction.selection,
        prediction.confidence_score,
        prediction.simulation_probability,
        prediction.projected_edge,
        prediction.odds_snapshot_id,
    ) == before