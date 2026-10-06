from datetime import UTC, datetime, timedelta
import random
from math import isnan
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, literal, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import attributes, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import predictions as predictions_api
from app.api.v1 import product as product_api, parlays as parlays_api
from app.auth.dependencies import get_current_user, require_analyst, require_viewer
from app.database.base import Base
from app.database.session import get_db
from app.models.game import Game
from app.models.model_registry import ModelRegistry
from app.models.model_version import ModelVersion
from app.models.npi_factor_result import NPIFactorResult
from app.models.npi_weight_profile import NPIWeightProfile
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.user_prediction import UserPrediction
from app.services.parlay_optimizer_service import ParlayOptimizerService
from app.services.npi_engine import NPIEngine
from app.services.prediction_engine import PredictionEngine
from app.services.prediction_metric_contract import (
    actionable_prediction, parse_market, parse_selection, sql_market, sql_selection,
)
from app.services.prediction_publication import canonical_predictions, canonical_prediction_id_query
from app.services.result_settlement_service import ResultSettlementService
from app.services.v1_read_service import V1ReadService
from app.services.final_score_settlement_service import FinalScoreSettlementService


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def add_game(db, index=1, days=1):
    home = Team(name=f"Home {index}", sport="NFL", league="NFL")
    away = Team(name=f"Away {index}", sport="NFL", league="NFL")
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport="NFL", league="NFL", home_team_id=home.id, away_team_id=away.id,
        game_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days),
        status="scheduled",
    )
    db.add(game)
    db.flush()
    odds = Odds(
        game_id=game.id, sportsbook="Test Book", spread_home=-2.5, spread_away=2.5,
        moneyline_home=-110, moneyline_away=100, total=40.5,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(odds)
    db.flush()
    return game, odds


def add_prediction(db, game, odds, *, version="NPI-4.0", market="spread", selection="HOME"):
    prediction = Prediction(
        game_id=game.id, model_version=version, market=market, selection=selection,
        npi_score=150, confidence_score=80, risk_level="low", simulation_probability=65,
        projected_edge=15, line_value=odds.total if market == "total" else odds.spread_home,
        american_odds=-110, odds_snapshot_id=odds.id, sportsbook=odds.sportsbook,
        odds_observed_at=odds.created_at,
    )
    db.add(prediction)
    db.flush()
    return prediction


@pytest.mark.parametrize("legacy_version", ["NPI-4.0", "NPI-4.1"])
def test_real_legacy_runtime_profile_generation_settlement_customer_lifecycle(db, legacy_version):
    weights = {
        "home_advantage": 80, "spread_value": 40, "market_environment": 30,
        "situational_edge": 30, "historical_rules": 20,
    }
    db.add(ModelRegistry(
        model_name="Production NFL", sport="NFL", version=legacy_version[4:],
        model_version=legacy_version, is_active=True, production_status=True,
    ))
    db.add(ModelVersion(
        model_name="Production NFL", sport="NFL", version=legacy_version, status="production",
    ))
    for name, weight in weights.items():
        db.add(NPIWeightProfile(
            sport="NFL", model_version=legacy_version, factor_name=name, weight=weight,
            is_active=True,
        ))
    game, odds = add_game(db)
    legacy = [
        add_prediction(db, game, odds, version=legacy_version, market=market,
                       selection="OVER" if market == "total" else "HOME")
        for market in ("spread", "moneyline", "total")
    ]
    db.commit()
    state = random.getstate()
    try:
        random.seed(41)
        corrected = PredictionEngine().analyze_markets(db, game.id, persist=True)
    finally:
        random.setstate(state)

    assert len(corrected) == 3
    assert all(row.model_version == "NPI-5.0" and row.selection != "PASS" for row in corrected)
    spread = next(row for row in corrected if row.market == "spread")
    factors = db.query(NPIFactorResult).filter_by(prediction_id=spread.id).all()
    assert {
        NPIEngine.LEGACY_FACTOR_NAMES[factor.factor_name]: factor.weight
        for factor in factors
    } == weights
    assert spread.npi_score == 154.5
    assert sum(factor.factor_score for factor in factors) == spread.npi_score
    assert db.query(ModelRegistry).count() == db.query(ModelVersion).count() == 1
    assert db.query(ModelRegistry).one().model_version == legacy_version
    assert db.query(ModelVersion).one().version == legacy_version
    assert db.query(NPIWeightProfile).count() == 5
    assert db.query(Prediction).count() == 6
    assert all(row.model_version == legacy_version and row.confidence_score == 80 for row in legacy)
    service = V1ReadService()
    assert {row["prediction_id"] for row in service.get_game_detail(db, game.id)["predictions"]} == {
        row.id for row in corrected
    }

    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    assert ResultSettlementService().settle_game(db, game.id)["settled"] == 6
    assert db.query(PredictionResult).count() == 6
    assert service.get_performance(db)["total_predictions"] == 3
    intelligence = service.get_performance_intelligence(db)
    assert intelligence["overall"]["total_bets"] == 3
    versions = {row["key"]: row["total_bets"] for row in intelligence["by_model_version"]}
    assert versions == {legacy_version: 3, "NPI-5.0": 3}
    assert not db.dirty


@pytest.mark.parametrize("old_version", ["NPI-4.0", "NPI-5.0"])
def test_latest_pass_advances_slate_without_resurrecting_old_actionable_pick(db, old_version):
    game, odds = add_game(db, days=1)
    old = add_prediction(db, game, odds, version=old_version)
    current = add_prediction(db, game, odds, version="NPI-5.0", selection="PASS")
    # A late legacy worker write must not supersede corrected PASS semantics.
    late_old = add_prediction(db, game, odds)
    next_game, next_odds = add_game(db, index=2, days=2)
    next_pick = add_prediction(db, next_game, next_odds, version="NPI-5.0")
    db.commit()
    service = V1ReadService()
    assert canonical_predictions([late_old, current, old]) == [current]
    assert service.resolve_slate_date(db) == next_game.game_date.date()
    assert [row["prediction_id"] for row in service.get_today_predictions(db)["predictions"]] == [next_pick.id]
    assert [row["prediction_id"] for row in service.get_upcoming_predictions(db)["predictions"]] == [next_pick.id]
    assert service.get_daily_card(db)["best_bet"]["prediction"]["prediction_id"] == next_pick.id
    detail = service.get_game_detail(db, game.id)["predictions"]
    assert len(detail) == 1 and detail[0]["selection"] == "PASS"
    assert detail[0]["recommendation_eligible"] is False
    now = datetime.now(UTC).replace(tzinfo=None)
    candidates = ParlayOptimizerService()._load_candidates(
        db, sport=None, now=now, horizon_end=now + timedelta(days=7),
    )
    assert [row["prediction_id"] for row in candidates] == [next_pick.id]
    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    ResultSettlementService().settle_game(db, game.id)
    assert service.get_performance(db)["total_predictions"] == 0
    assert service.get_performance_intelligence(db)["overall"]["total_bets"] == 0


def test_corrected_snapshot_supersession_preserves_history_and_is_idempotent(db):
    game, odds = add_game(db)
    state = random.getstate()
    try:
        random.seed(41)
        engine = PredictionEngine()
        first = engine.analyze_markets(db, game.id, persist=True)
        new_odds = Odds(
            game_id=game.id, sportsbook=odds.sportsbook,
            spread_home=-3.5, spread_away=3.5, moneyline_home=-120,
            moneyline_away=110, total=48.5, created_at=odds.created_at + timedelta(seconds=1),
        )
        db.add(new_odds)
        db.commit()
        second = engine.analyze_markets(db, game.id, persist=True)
        third = engine.analyze_markets(db, game.id, persist=True)
    finally:
        random.setstate(state)
    assert db.query(Prediction).count() == 6
    assert {row.id for row in first}.isdisjoint(row.id for row in second)
    assert [row.id for row in second] == [row.id for row in third]
    assert all(db.get(Prediction, row.id).odds_snapshot_id == odds.id for row in first)
    assert all(row.odds_snapshot_id == new_odds.id for row in second)
    assert db.query(NPIFactorResult).filter(
        NPIFactorResult.prediction_id.in_([row.id for row in first]),
    ).count() == 7


@pytest.mark.parametrize("invalid", [101, -1, float("inf")])
def test_stored_endpoint_adapts_invalid_historical_probability_without_mutation(db, invalid, caplog):
    game, odds = add_game(db)
    prediction = add_prediction(db, game, odds)
    prediction.simulation_probability = invalid
    db.commit()
    test_app = FastAPI()
    test_app.include_router(predictions_api.router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: db
    test_app.dependency_overrides[require_analyst] = lambda: object()
    with TestClient(test_app) as client:
        response = client.get("/api/v1/predictions/stored")
    assert response.status_code == 200
    assert response.json()[0]["simulation_probability"] is None
    assert caplog.records
    db.expire_all()
    assert db.get(Prediction, prediction.id).simulation_probability == invalid
    assert not db.dirty


def test_unsettled_corrected_row_does_not_resurrect_a_legacy_settlement(db):
    game, odds = add_game(db)
    old = add_prediction(db, game, odds)
    db.add(PredictionResult(
        prediction_id=old.id, actual_result="HOME", predicted_result="HOME",
        outcome="WIN", profit_loss=100,
    ))
    add_prediction(db, game, odds, version="NPI-5.0")
    db.commit()
    assert V1ReadService().get_performance(db)["total_predictions"] == 0
    assert V1ReadService().get_performance_intelligence(db)["overall"]["total_bets"] == 0


def test_cross_market_daily_card_and_parlay_edge_ordering_uses_threshold_multiples(db):
    daily = []
    components = []
    for index, (market, edge) in enumerate([("spread", 5), ("moneyline", 3), ("total", 2)], 1):
        game, odds = add_game(db, index=index)
        prediction = add_prediction(
            db, game, odds, version="NPI-5.0", market=market,
            selection="OVER" if market == "total" else "HOME",
        )
        prediction.projected_edge = edge
        daily.append({
            "market": market, "selection": prediction.selection, "model_version": "NPI-5.0",
            "npi_score": 150, "confidence_score": 80, "simulation_probability": 65,
            "projected_edge": edge, "american_odds": -110, "risk_level": "low",
        })
        components.append(ParlayOptimizerService()._score(
            prediction, datetime.now(UTC).replace(tzinfo=None),
        )[1]["edge_ranking_strength"])
    assert components == [7.5, 7.5, 7.5]
    service = V1ReadService()
    scores = [service._daily_card_score(item) for item in daily]
    assert scores[0] == scores[1] == scores[2]
    # A 3-point total outranks a 6-pp spread on edge strength, not raw magnitude.
    daily[2]["projected_edge"], daily[0]["projected_edge"] = 3, 6
    assert service._daily_card_score(daily[2]) > service._daily_card_score(daily[0])


@pytest.fixture
def client(db):
    test_app = FastAPI()
    for router in (product_api.router, predictions_api.router, parlays_api.router):
        test_app.include_router(router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: db
    for dependency in (get_current_user, require_analyst, require_viewer):
        test_app.dependency_overrides[dependency] = lambda: object()
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.mark.parametrize("missing_field", ["line_value", "american_odds"])
def test_settlement_isolates_incomplete_legacy_and_is_idempotent(db, missing_field, caplog):
    game, odds = add_game(db)
    legacy = add_prediction(db, game, odds)
    setattr(legacy, missing_field, None)
    corrected = [
        add_prediction(db, game, odds, version="NPI-5.0", market=market,
                       selection="OVER" if market == "total" else "HOME")
        for market in ("spread", "moneyline", "total")
    ]
    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    original = {column.name: getattr(legacy, column.name) for column in Prediction.__table__.columns}
    service = ResultSettlementService()
    response = service.settle_game(db, game.id)
    assert response["settled"] == 3
    assert response["skipped"][0]["prediction_id"] == legacy.id
    assert ("line snapshot" if missing_field == "line_value" else "odds snapshot") in response["skipped"][0]["reason"]
    assert any(str(legacy.id) in record.message and "Skipping" in record.message for record in caplog.records)
    assert {row.prediction_id for row in db.query(PredictionResult)} == {row.id for row in corrected}
    assert {column.name: getattr(legacy, column.name) for column in Prediction.__table__.columns} == original
    repeated = service.settle_game(db, game.id)
    assert repeated["settled"] == 0 and repeated["skipped"] == response["skipped"]
    assert db.query(PredictionResult).count() == 3
    assert V1ReadService().get_performance(db)["total_predictions"] == 3
    assert V1ReadService().get_performance_intelligence(db)["overall"]["total_bets"] == 3


def test_unexpected_settlement_failure_propagates_and_transaction_can_rollback(db, monkeypatch):
    game, odds = add_game(db)
    first = add_prediction(db, game, odds)
    second = add_prediction(db, game, odds, market="total", selection="OVER")
    game.home_score, game.away_score = 31, 21
    db.commit()
    service = ResultSettlementService()
    grade = service.grade_prediction

    def failing_grade(**kwargs):
        if kwargs["prediction"].id == second.id:
            raise RuntimeError("unexpected programming failure")
        return grade(**kwargs)

    monkeypatch.setattr(service, "grade_prediction", failing_grade)
    with pytest.raises(RuntimeError, match="unexpected programming failure"):
        service.settle_game(db, game.id)
    db.rollback()
    assert db.query(PredictionResult).count() == 0
    assert db.get(Prediction, first.id) is not None


INVALID_COMPLETENESS = [
    ("confidence_score", None), ("confidence_score", float("nan")), ("confidence_score", float("inf")),
    ("projected_edge", None), ("projected_edge", float("nan")), ("projected_edge", float("inf")),
    ("simulation_probability", None), ("simulation_probability", 101),
    ("simulation_probability", float("nan")), ("simulation_probability", float("inf")),
    ("npi_score", None), ("npi_score", float("nan")), ("npi_score", float("inf")),
    ("line_value", None), ("line_value", float("nan")), ("line_value", float("inf")),
    ("american_odds", None), ("american_odds", 0), ("american_odds", "bad"),
    ("american_odds", float("nan")), ("american_odds", float("inf")),
    ("american_odds", 50), ("american_odds", -110.5),
    ("market", None), ("market", ""), ("market", 123), ("market", "unsupported"),
    ("selection", None), ("selection", ""), ("selection", 123), ("selection", "PASS"),
    ("selection", "OVER"), ("model_version", None), ("model_version", ""),
    ("model_version", 123), ("model_version", "NPI-5.1"),
]


@pytest.mark.parametrize(("field", "value"), INVALID_COMPLETENESS)
def test_shared_completeness_excludes_invalid_daily_and_parlay_candidates(db, field, value):
    game, odds = add_game(db)
    row = add_prediction(db, game, odds, version="NPI-5.0")
    db.commit()
    # Exercise malformed driver/runtime values without writing invalid test data.
    attributes.set_committed_value(row, field, value)
    assert not actionable_prediction(row)
    service = V1ReadService()
    payload = {
        column.name: getattr(row, column.name) for column in Prediction.__table__.columns
    }
    payload["prediction_id"] = row.id
    card = service._build_daily_card([payload])
    assert card["best_bet"] is None and card["featured_picks"] == [] and card["next_best"] == []
    now = datetime.now(UTC).replace(tzinfo=None)
    assert ParlayOptimizerService()._load_candidates(
        db, sport=None, now=now, horizon_end=now + timedelta(days=7),
    ) == []
    assert not db.dirty


@pytest.mark.parametrize("market,selection", [("spread", "AWAY"), ("total", "UNDER"), ("moneyline", "HOME")])
def test_completeness_market_lines_and_valid_selected_sides(db, market, selection):
    game, odds = add_game(db)
    row = add_prediction(db, game, odds, version="NPI-5.0", market=market, selection=selection)
    assert actionable_prediction(row)
    row.line_value = None
    assert actionable_prediction(row) is (market == "moneyline")


@pytest.mark.parametrize("field", ["confidence_score", "projected_edge", "line_value", "american_odds"])
def test_incomplete_canonical_advances_slate_without_resurrecting_history(db, field):
    game, odds = add_game(db)
    add_prediction(db, game, odds)
    current = add_prediction(db, game, odds, version="NPI-5.0")
    setattr(current, field, None)
    late = add_prediction(db, game, odds, version="NPI-4.1")
    next_game, next_odds = add_game(db, index=2, days=2)
    next_pick = add_prediction(db, next_game, next_odds, version="NPI-5.0")
    db.commit()
    service = V1ReadService()
    assert service.resolve_slate_date(db) == next_game.game_date.date()
    assert [row["prediction_id"] for row in service.get_upcoming_predictions(db)["predictions"]] == [next_pick.id]
    assert service.get_daily_card(db)["best_bet"]["prediction"]["prediction_id"] == next_pick.id
    detail = service.get_game_detail(db, game.id)["predictions"]
    assert len(detail) == 1 and detail[0]["prediction_id"] == current.id
    assert not detail[0]["recommendation_eligible"]
    assert late.id != detail[0]["prediction_id"]


@pytest.mark.parametrize("field", [
    "simulation_probability", "confidence_score", "projected_edge", "npi_score",
    "line_value", "american_odds",
])
@pytest.mark.parametrize("invalid", [float("inf"), float("-inf"), float("nan")])
def test_historical_numeric_endpoints_are_nullable_and_do_not_mutate(db, client, caplog, field, invalid):
    game, odds = add_game(db)
    row = add_prediction(db, game, odds, version="NPI-5.0")
    # SQLite converts NaN to NULL (and NPI is NOT NULL); emulate a PostgreSQL
    # driver's NaN value in the identity map, leaving the persisted infinity intact.
    stored = float("inf") if isnan(invalid) else invalid
    setattr(row, field, stored)
    db.commit()
    attributes.set_committed_value(row, field, invalid)
    detail = client.get(f"/api/v1/product/games/{game.id}")
    assert detail.status_code == 200
    item = detail.json()["predictions"][0]
    assert item[field] is None and not item["recommendation_eligible"]
    stored_response = client.get("/api/v1/predictions/stored")
    assert stored_response.status_code == 200 and stored_response.json()[0][field] is None
    analyst_listing = client.get("/api/v1/predictions")
    assert analyst_listing.status_code == 200 and analyst_listing.json()[0][field] is None
    for endpoint in ("daily-card", "predictions/upcoming", "predictions/today"):
        response = client.get(f"/api/v1/product/{endpoint}")
        assert response.status_code == 200
        payload = response.json()
        if endpoint == "daily-card":
            assert payload["best_bet"] is None and payload["featured_picks"] == []
        else:
            assert payload["predictions"] == []
    informational = client.get("/api/v1/product/predictions/upcoming?include_passes=true")
    assert informational.status_code == 200
    assert informational.json()["predictions"][0][field] is None
    parlay = client.get("/api/v1/parlays/optimize?legs=2")
    assert parlay.status_code == 422  # no valid inventory, never a fabricated leg
    assert caplog.records
    persisted = db.execute(select(getattr(Prediction, field)).where(Prediction.id == row.id)).scalar_one()
    assert persisted == stored and not db.dirty


def test_public_parlay_recursively_omits_internal_strength_and_preserves_metrics(db, client):
    for index, market in enumerate(("spread", "total"), 1):
        game, odds = add_game(db, index=index)
        add_prediction(db, game, odds, version="NPI-5.0", market=market,
                       selection="OVER" if market == "total" else "HOME")
    db.commit()
    response = client.get("/api/v1/parlays/optimize?legs=2")
    assert response.status_code == 200

    def check(value):
        if isinstance(value, dict):
            assert not {"edge_ranking_strength", "score_components", "parlay_score", "ranking_score"} & value.keys()
            for nested in value.values():
                check(nested)
        elif isinstance(value, list):
            for nested in value:
                check(nested)

    check(response.json())
    check(client.get("/api/v1/product/daily-card").json())
    check(client.get("/api/v1/product/predictions/upcoming").json())
    for leg in response.json()["legs"]:
        assert all(leg[key] is not None for key in (
            "projected_edge", "selected_side_edge", "edge_unit", "simulation_probability",
            "npi_score", "confidence_score",
        ))


def test_rollback_compatible_reader_preserves_mixed_version_counts_and_probability(db):
    game, odds = add_game(db)
    legacy = add_prediction(db, game, odds, version="NPI-4.1", selection="AWAY")
    legacy.simulation_probability, legacy.projected_edge = 30, -20
    corrected = add_prediction(db, game, odds, version="NPI-5.0", selection="AWAY")
    corrected.simulation_probability, corrected.projected_edge = 70, 20
    late = add_prediction(db, game, odds, selection="AWAY")
    late.simulation_probability, late.projected_edge = 30, -20
    game.status, game.home_score, game.away_score = "final", 21, 31
    db.commit()
    ResultSettlementService().settle_game(db, game.id)
    compatible_reader = V1ReadService()
    item = compatible_reader.get_game_detail(db, game.id)["predictions"][0]
    assert item["prediction_id"] == corrected.id and item["simulation_probability"] == 70
    assert compatible_reader.get_performance(db)["total_predictions"] == 1
    report = compatible_reader.get_performance_intelligence(db)
    assert report["overall"]["total_bets"] == 1
    assert sum(row["total_bets"] for row in report["by_model_version"]) == 3
    assert db.query(Prediction).count() == db.query(PredictionResult).count() == 3


def test_sql_canonical_selection_bounds_materialized_generations(db):
    current_ids = []
    for index in range(1, 5):
        game, odds = add_game(db, index=index)
        for _ in range(100):
            add_prediction(db, game, odds)
        current = add_prediction(db, game, odds, version="NPI-5.0")
        current_ids.append(current.id)
        for _ in range(10):
            add_prediction(db, game, odds, version="NPI-4.1")
        if index == 3:
            current.selection = "PASS"
        if index == 4:
            current.confidence_score = None
    db.commit()
    assert db.query(Prediction).count() == 444
    db.expunge_all()
    loaded = []
    statements = []

    def track_loaded(session, instance):
        if isinstance(instance, Prediction):
            loaded.append(instance.id)

    def track_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db, "loaded_as_persistent", track_loaded)
    event.listen(db.bind, "before_cursor_execute", track_sql)
    try:
        feed = V1ReadService().get_upcoming_predictions(db)
    finally:
        event.remove(db, "loaded_as_persistent", track_loaded)
        event.remove(db.bind, "before_cursor_execute", track_sql)
    assert [row["prediction_id"] for row in feed["predictions"]] == list(reversed(current_ids[:2]))
    assert set(loaded) == set(current_ids) and len(loaded) == 4
    assert len(statements) == 1 and "row_number()" in statements[0].lower()
    assert set(db.scalars(canonical_prediction_id_query())) == set(current_ids)
    page = db.query(Prediction).filter(
        Prediction.id.in_(canonical_prediction_id_query()),
        Prediction.selection != "PASS", Prediction.confidence_score.is_not(None),
    ).order_by(Prediction.id.desc()).limit(1).all()
    assert [row.id for row in page] == [current_ids[1]]
    for prediction_id in db.scalars(select(Prediction.id)):
        db.add(PredictionResult(
            prediction_id=prediction_id, actual_result="HOME", predicted_result="HOME",
            outcome="WIN", profit_loss=100,
        ))
    db.commit()
    db.expunge_all()
    loaded.clear()
    statements.clear()
    event.listen(db, "loaded_as_persistent", track_loaded)
    event.listen(db.bind, "before_cursor_execute", track_sql)
    try:
        performance = V1ReadService().get_performance(db)
    finally:
        event.remove(db, "loaded_as_persistent", track_loaded)
        event.remove(db.bind, "before_cursor_execute", track_sql)
    assert performance["total_predictions"] == 3
    assert set(loaded) == {current_ids[0], current_ids[1], current_ids[3]}
    assert len(loaded) == 3 and len(statements) == 1
    db.expunge_all()
    peak_predictions = []

    def track_peak(session, instance):
        peak_predictions.append(sum(isinstance(row, Prediction) for row in session.identity_map.values()))

    event.listen(db, "loaded_as_persistent", track_peak)
    try:
        intelligence = V1ReadService().get_performance_intelligence(db)
    finally:
        event.remove(db, "loaded_as_persistent", track_peak)
    assert intelligence["overall"]["total_bets"] == 3
    assert sum(row["total_bets"] for row in intelligence["by_model_version"]) == 12
    assert intelligence["npi_4_spread"]["summary"]["sample_size"] == 4
    assert max(peak_predictions) <= 15


def metadata_variant(token, variant):
    if variant == 0:
        return token
    if variant == 1:
        return f" {token} "
    if variant == 2:
        return f"\t{token}\t"
    if variant == 3:
        return f"\r\n{token}\n\r"
    if variant == 4:
        return token.swapcase()
    return " \t\r\n".join(token.swapcase())


@pytest.mark.parametrize("token", ["spread", "moneyline", "total", "HOME", "AWAY", "OVER", "UNDER", "PASS"])
@pytest.mark.parametrize("variant", range(6))
def test_metadata_python_sql_normalization_parity(db, token, variant):
    value = metadata_variant(token, variant)
    python_market, python_selection = parse_market(value), parse_selection(value)
    sql_values = db.execute(select(sql_market(literal(value)), sql_selection(literal(value)))).one()
    assert sql_values == (python_market, python_selection)
    assert python_market == (token if token.islower() else None)
    assert python_selection == (token if token.isupper() else None)


@pytest.mark.parametrize("value", ["", " \t\r\n", "ats", "ml", "totals", "unknown", "HOMES", "\vHOME", "spread\u00a0", "pa\u017fs", None])
def test_unsupported_metadata_is_unavailable_in_python_and_sql(db, value):
    assert parse_market(value) is None and parse_selection(value) is None
    assert db.execute(select(sql_market(literal(value)), sql_selection(literal(value)))).one() == (None, None)


def test_sql_canonical_postgresql_compile_and_normalized_supersession(db):
    game, odds = add_game(db)
    old = add_prediction(db, game, odds)
    current = add_prediction(db, game, odds, version="NPI-5.0", market=" \tSpReAd\r\n", selection="\tHoMe\r")
    late = add_prediction(db, game, odds, version="NPI-4.1")
    malformed = add_prediction(db, game, odds, version="NPI-5.0", selection="unknown")
    unrelated = add_prediction(db, game, odds, version="NPI-5.0", market="spread_unknown")
    unsupported_version = add_prediction(db, game, odds, version="NPI-9.0")
    db.commit()
    assert set(db.scalars(canonical_prediction_id_query())) == {current.id}
    assert canonical_predictions([old, current, late, malformed, unrelated, unsupported_version]) == [current]
    query = canonical_prediction_id_query().compile(dialect=postgresql.dialect())
    assert "row_number()" in str(query) and "replace(" in str(query)
    assert "trim(" not in str(query)
    assert {current.id} == {row["prediction_id"] for row in V1ReadService().get_upcoming_predictions(db)["predictions"]}
    current.selection = "\tPaSs\r\n"
    db.commit()
    assert set(db.scalars(canonical_prediction_id_query())) == {current.id}
    assert V1ReadService().get_upcoming_predictions(db)["predictions"] == []
    current.selection = "unknown"
    db.commit()
    assert set(db.scalars(canonical_prediction_id_query())) == {late.id}
    assert canonical_predictions([old, current, late, malformed, unrelated, unsupported_version]) == [late]


@pytest.mark.parametrize("variant", range(6))
@pytest.mark.parametrize("version", ["NPI-4.0", "NPI-4.1", "NPI-5.0"])
@pytest.mark.parametrize(("market", "selection"), [
    ("spread", "HOME"), ("spread", "AWAY"), ("moneyline", "HOME"),
    ("moneyline", "AWAY"), ("total", "OVER"), ("total", "UNDER"),
])
def test_metadata_variants_end_to_end_identity_display_and_settlement(
    db, client, monkeypatch, variant, version, market, selection,
):
    game, odds = add_game(db)
    row = add_prediction(
        db, game, odds, version=version,
        market=metadata_variant(market, variant), selection=metadata_variant(selection, variant),
    )
    row.line_value = (
        odds.spread_home if selection == "HOME" else odds.spread_away
    ) if market == "spread" else odds.total if market == "total" else None
    row.american_odds = (
        odds.moneyline_home if selection == "HOME" else odds.moneyline_away
    ) if market == "moneyline" else -110
    row.simulation_probability = 35 if version != "NPI-5.0" and market == "spread" and selection == "AWAY" else 65
    row.projected_edge = -15 if version != "NPI-5.0" and (
        (market == "spread" and selection == "AWAY") or (market == "total" and selection == "UNDER")
    ) else 15
    db.add(UserPrediction(user_id=42, prediction_id=row.id))
    db.commit()
    original = (row.market, row.selection, row.line_value, row.american_odds, row.simulation_probability)
    monkeypatch.setattr(product_api, "resolve_persistent_user_id", lambda *_: 42)
    expected = (
        f"{'Home 1' if selection == 'HOME' else 'Away 1'} {row.line_value:+g}" if market == "spread"
        else f"{'Home 1' if selection == 'HOME' else 'Away 1'} ML" if market == "moneyline"
        else f"{selection} {row.line_value:g}"
    )
    detail = client.get(f"/api/v1/product/games/{game.id}").json()["predictions"][0]
    daily = client.get("/api/v1/product/daily-card").json()["best_bet"]["prediction"]
    today = client.get("/api/v1/product/predictions/today").json()["predictions"][0]
    upcoming = client.get("/api/v1/product/predictions/upcoming").json()["predictions"][0]
    saved = client.get("/api/v1/product/me/saved-picks").json()["picks"][0]
    for item in (detail, daily, today, upcoming, saved):
        assert item["prediction_id"] == row.id and item["display_selection"] == expected
        assert item["market"] == market and item["selection"] == selection
        assert item["line_value"] == original[2] and item["american_odds"] == original[3]
    for item in (detail, daily, today, upcoming):
        assert item["simulation_probability"] == 65 and item["selected_side_edge"] == 15
        assert item["recommendation_eligible"]
    now = datetime.now(UTC).replace(tzinfo=None)
    candidate = ParlayOptimizerService()._load_candidates(
        db, sport=None, now=now, horizon_end=now + timedelta(days=7),
    )[0]
    assert candidate["prediction_id"] == row.id
    assert candidate["market"] == market and candidate["selection"] == selection
    assert candidate["line_value"] == original[2] and candidate["american_odds"] == original[3]
    assert candidate["simulation_probability"] == 65 and candidate["selected_side_edge"] == 15
    assert expected in candidate["display_selection"]
    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    settlement = ResultSettlementService().settle_game(db, game.id)
    expected_outcome = "WIN" if selection in {"HOME", "OVER"} else "LOSS"
    assert settlement["settled"] == 1 and settlement["results"][0]["outcome"] == expected_outcome
    performance = client.get("/api/v1/product/performance").json()
    assert performance["total_predictions"] == 1
    assert performance["recent_results"][0]["display_selection"] == expected
    assert client.get("/api/v1/product/me/saved-picks").json()["picks"][0]["outcome"] == expected_outcome
    assert (row.market, row.selection, row.line_value, row.american_odds, row.simulation_probability) == original
    assert not db.dirty


@pytest.mark.parametrize("variant", range(6))
def test_normalized_pass_never_counts_as_customer_bet(db, client, variant):
    game, odds = add_game(db)
    add_prediction(db, game, odds)
    current = add_prediction(
        db, game, odds, version="NPI-5.0",
        market=metadata_variant("spread", variant), selection=metadata_variant("PASS", variant),
    )
    db.commit()
    detail = client.get(f"/api/v1/product/games/{game.id}").json()["predictions"][0]
    assert detail["prediction_id"] == current.id and detail["display_selection"] == "PASS"
    assert detail["selection"] == "PASS" and not detail["recommendation_eligible"]
    assert client.get("/api/v1/product/daily-card").json()["best_bet"] is None
    assert client.get("/api/v1/product/predictions/upcoming").json()["predictions"] == []
    now = datetime.now(UTC).replace(tzinfo=None)
    assert ParlayOptimizerService()._load_candidates(db, None, now, now + timedelta(days=7)) == []
    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    ResultSettlementService().settle_game(db, game.id)
    assert V1ReadService().get_performance(db)["total_predictions"] == 0
    assert V1ReadService().get_performance_intelligence(db)["overall"]["total_bets"] == 0


@pytest.mark.parametrize("selection", ["", " \t\r\n", "unsupported", "OVER"])
def test_malformed_selection_has_no_team_default_or_customer_bet(db, client, selection):
    game, odds = add_game(db)
    row = add_prediction(db, game, odds, version="NPI-5.0", selection=selection)
    db.commit()
    detail = client.get(f"/api/v1/product/games/{game.id}").json()["predictions"][0]
    assert detail["selection"] == "unavailable" and detail["display_selection"] == "Selection unavailable"
    assert detail["simulation_probability"] is None and not detail["recommendation_eligible"]
    game.status, game.home_score, game.away_score = "final", 31, 21
    db.commit()
    response = ResultSettlementService().settle_game(db, game.id)
    assert response["settled"] == 0 and response["skipped"][0]["prediction_id"] == row.id
    assert V1ReadService().get_performance(db)["total_predictions"] == 0


@pytest.fixture
def postgres_engine():
    url = os.getenv("METRIC_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("Set METRIC_TEST_POSTGRES_URL to a disposable local PostgreSQL test database")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or parsed.host not in {"127.0.0.1", "localhost"} or parsed.database != "metric_integrity_test":
        pytest.fail("PostgreSQL concurrency fixture permits only local metric_integrity_test")
    admin = create_engine(url)
    schema = f"metric_test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        Base.metadata.create_all(engine, tables=[
            Base.metadata.tables[name] for name in (
                "teams", "games", "odds", "predictions", "prediction_results",
                "ncaaf_rule_intelligence",
            )
        ])
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def seed_postgres_settlement(engine):
    with sessionmaker(bind=engine)() as db:
        game, odds = add_game(db)
        legacy = add_prediction(db, game, odds)
        legacy.line_value = None
        rows = [
            add_prediction(db, game, odds, version="NPI-5.0", market=market,
                           selection="OVER" if market == "total" else "HOME")
            for market in ("spread", "moneyline", "total")
        ]
        game.status, game.home_score, game.away_score = "final", 31, 21
        db.commit()
        return game.id, legacy.id, [row.id for row in rows]


def test_postgresql_concurrent_settlement_waits_and_returns_already_settled(postgres_engine, caplog):
    game_id, legacy_id, corrected_ids = seed_postgres_settlement(postgres_engine)
    locked, release, second_started = Event(), Event(), Event()
    second_pid = []

    def attempt(hold):
        with sessionmaker(bind=postgres_engine)() as db:
            service = ResultSettlementService()
            if hold:
                grade = service.grade_prediction

                def pause_after_lock(**kwargs):
                    if not locked.is_set():
                        locked.set()
                        assert release.wait(15), "Timed out waiting to release test lock"
                    return grade(**kwargs)

                service.grade_prediction = pause_after_lock
            else:
                second_pid.append(db.scalar(text("SELECT pg_backend_pid()")))
                second_started.set()
            try:
                return service.settle_game(db, game_id)
            except Exception:
                db.rollback()
                raise

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(attempt, True)
        assert locked.wait(10)
        second = executor.submit(attempt, False)
        assert second_started.wait(10)
        try:
            deadline = time.monotonic() + 10
            blocked = False
            with postgres_engine.connect() as monitor:
                while time.monotonic() < deadline:
                    blocked = bool(monitor.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid))"), {"pid": second_pid[0]},
                    ))
                    if blocked:
                        break
                    time.sleep(0.02)
            assert blocked and not second.done(), "Second PostgreSQL session did not wait on the Game lock"
        finally:
            release.set()
        responses = [first.result(timeout=10), second.result(timeout=10)]
    assert [response["settled"] for response in responses] == [3, 0]
    assert all(response["skipped"][0]["prediction_id"] == legacy_id for response in responses)
    assert all(item["status"] == "already_settled" for item in responses[1]["results"])
    assert not [record for record in caplog.records if record.levelname == "ERROR"]
    with sessionmaker(bind=postgres_engine)() as db:
        assert {result.prediction_id for result in db.query(PredictionResult)} == set(corrected_ids)
        assert db.get(Prediction, legacy_id).line_value is None
        assert ResultSettlementService().settle_game(db, game_id)["settled"] == 0
        assert V1ReadService().get_performance(db)["total_predictions"] == 3


@pytest.mark.parametrize("failure", ["programming", "database"])
def test_postgresql_unexpected_later_failure_rolls_back_all_results(postgres_engine, failure):
    game_id, _, corrected_ids = seed_postgres_settlement(postgres_engine)
    with sessionmaker(bind=postgres_engine)() as db:
        service = ResultSettlementService()
        grade = service.grade_prediction

        def failing_grade(**kwargs):
            if kwargs["prediction"].id == corrected_ids[1]:
                if failure == "programming":
                    raise RuntimeError("unexpected programming failure")
                db.add(PredictionResult(
                    prediction_id=corrected_ids[1], actual_result=None,
                    predicted_result="HOME", outcome="WIN", profit_loss=100,
                ))
                db.flush()
            return grade(**kwargs)

        service.grade_prediction = failing_grade
        with pytest.raises(RuntimeError if failure == "programming" else IntegrityError):
            service.settle_game(db, game_id)
        db.rollback()
        assert db.query(PredictionResult).count() == 0
        assert ResultSettlementService().settle_game(db, game_id)["settled"] == 3


def test_postgresql_metadata_sql_parity_and_worker_response(postgres_engine):
    with sessionmaker(bind=postgres_engine)() as db:
        game, odds = add_game(db)
        game.provider_game_id = "metric-worker-test"
        add_prediction(db, game, odds)
        current = add_prediction(
            db, game, odds, version="NPI-5.0", market="s\tPr\rEa\nd", selection="\tPaSs\r\n",
        )
        incomplete = add_prediction(db, game, odds, market="total", selection="OVER")
        incomplete.line_value = None
        db.commit()
        assert set(db.scalars(canonical_prediction_id_query())) == {current.id, incomplete.id}
        assert {row.id for row in canonical_predictions(db.query(Prediction).all())} == {current.id, incomplete.id}
        for token in ("spread", "HOME", "PASS", "unknown", ""):
            for variant in range(6):
                value = metadata_variant(token, variant)
                assert db.execute(select(sql_market(literal(value)), sql_selection(literal(value)))).one() == (
                    parse_market(value), parse_selection(value),
                )

        class ScoreClient:
            def get_scores(self, *_args, **_kwargs):
                return [{
                    "id": "metric-worker-test", "completed": True,
                    "home_team": "Home 1", "away_team": "Away 1",
                    "scores": [{"name": "Home 1", "score": "31"}, {"name": "Away 1", "score": "21"}],
                }]

        worker = FinalScoreSettlementService(provider_client=ScoreClient())
        summary = worker.sync_sport(db, "NFL")
        assert summary.errors == 0 and summary.settled == 1
        assert db.query(PredictionResult).count() == 2
        assert V1ReadService().get_performance(db)["total_predictions"] == 0
        assert V1ReadService().get_performance_intelligence(db)["overall"]["total_bets"] == 0
        retry = worker.sync_sport(db, "NFL")
        assert retry.errors == 0 and retry.settled == 0


def test_postgresql_empty_game_releases_settlement_lock(postgres_engine):
    with sessionmaker(bind=postgres_engine)() as first:
        game, _ = add_game(first)
        game.status, game.home_score, game.away_score = "final", 31, 21
        first.commit()
        game_id = game.id
        assert ResultSettlementService().settle_game(first, game_id)["settled"] == 0
        with sessionmaker(bind=postgres_engine)() as second:
            second.execute(text("SET LOCAL lock_timeout = '1s'"))
            assert ResultSettlementService().settle_game(second, game_id) == {
                "game_id": game_id, "settled": 0, "results": [], "skipped": [],
            }
