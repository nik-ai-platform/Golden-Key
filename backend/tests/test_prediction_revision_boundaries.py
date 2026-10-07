from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import random
import sys
from pathlib import Path
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event as sql_event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.api.v1 import predictions as api
from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.models.model_version import ModelVersion
from app.models.ncaaf_rule_intelligence import NcaafRuleIntelligence
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.npi_factor_result import NPIFactorResult
from app.models.ai_analysis import AIAnalysis
from app.models.user_prediction import UserPrediction
from app.models.prediction_line_correction import PredictionLineCorrection
from app.schemas.prediction import PredictionCreate
from app.services.cache_service import cache_service
from app.services.model_evaluation import ModelEvaluation
from app.services.parlay_optimizer_service import ParlayOptimizerService
from app.services.performance_engine import PerformanceEngine
from app.services.prediction_publication import canonical_prediction_ids
from app.services.prediction_revision import input_fingerprint
from app.services.result_settlement_service import ResultSettlementService
from app.services.simulation_engine import SimulationEngine
from app.services.ai_analysis_engine import AIAnalysisEngine
from app.services.npi_engine import NPIEngine
from app.services.v1_read_service import V1ReadService
from test_prediction_refresh_idempotency import db, seed, frozen
from test_nba_preseason_sync import event, importer, prediction_engine
from scripts import regenerate_future_predictions as regeneration


def client(session):
    application = FastAPI()
    application.include_router(api.router, prefix="/api/v1")
    application.dependency_overrides[get_db] = lambda: session
    application.dependency_overrides[require_analyst] = lambda: object()
    return TestClient(application)


def alembic_config(connection=None):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "migrations"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def test_single_head_preserves_both_prior_branches():
    script = ScriptDirectory.from_config(alembic_config())
    assert script.get_heads() == ["a9b2e4d7c031"]
    assert script.get_revision("a9b2e4d7c031").down_revision == "f8a1d3c6b920"
    assert script.get_revision("f8a1d3c6b920").down_revision == "e7b4c2d9a610"
    assert script.get_revision("e7b4c2d9a610").down_revision == "c8d2f6a109b4"
    revision = script.get_revision("c8d2f6a109b4")
    assert set(revision.down_revision) == {"c6f2a8d4e913", "a4c8e2f19b73"}
    ancestors = {row.revision for row in script.walk_revisions()}
    assert {"a4c8e2f19b73", "c6f2a8d4e913", "f3a9c7d2e641"} <= ancestors


def payload(game, score=150):
    return PredictionCreate(
        game_id=game.id, model_version="NPI-5.0", market="spread",
        selection="HOME", npi_score=score,
    )


def test_post_endpoint_identical_writes_and_started_guard(db):
    game, _, _, _ = seed(db)
    http = client(db)
    body = payload(game).model_dump(mode="json")
    first = http.post("/api/v1/predictions/", json=body)
    second = http.post("/api/v1/predictions/", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert db.query(Prediction).count() == 1
    old = frozen(db.query(Prediction).one())
    changed = http.post("/api/v1/predictions/", json={**body, "npi_score": 151})
    assert changed.status_code == 200
    assert changed.json()["id"] != first.json()["id"]
    assert frozen(db.get(Prediction, first.json()["id"])) == old
    game.game_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    db.commit()
    rejected = http.post("/api/v1/predictions/", json={**body, "npi_score": 152})
    assert rejected.status_code == 400
    assert db.query(Prediction).count() == 2


def test_post_endpoint_concurrent_duplicates_postgres(db):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock test")
    game, _, _, _ = seed(db)
    body = payload(game).model_dump(mode="json")
    factory = sessionmaker(bind=db.bind)
    barrier = Barrier(2)
    def write():
        with factory() as session:
            barrier.wait(timeout=10)
            response = client(session).post("/api/v1/predictions/", json=body)
            assert response.status_code == 200
            return response.json()["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: write(), range(2)))
    assert first == second
    assert db.query(Prediction).count() == 1


def test_post_endpoint_unrecognized_historical_market_still_deduplicates(db):
    game, _, _, _ = seed(db)
    body = {**payload(game).model_dump(mode="json"), "market": "historical-custom"}
    http = client(db)
    first = http.post("/api/v1/predictions/", json=body)
    second = http.post("/api/v1/predictions/", json=body)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert db.query(Prediction).count() == 1


@pytest.mark.parametrize("field,value", [
    ("generation_id", None), ("generation_id", ""), ("generation_id", "bad"),
    ("input_fingerprint", None), ("input_fingerprint", ""), ("input_fingerprint", "bad"),
])
def test_null_and_invalid_revision_metadata_rejected(db, field, value):
    game, _, _, _ = seed(db)
    values = {
        **payload(game).model_dump(), "generation_id": str(uuid4()),
        "input_fingerprint": "unverified:manual",
    }
    values[field] = value
    with pytest.raises(IntegrityError):
        db.execute(Prediction.__table__.insert().values(**values))
    db.rollback()
    assert db.query(Prediction).count() == 0


def test_nonmaterial_model_and_game_metadata_does_not_republish(db):
    game, _, _, engine = seed(db)
    model = ModelVersion(
        model_name="NBA", sport="NBA", version="NPI-4.0", status="production",
        changes='{"b": 2, "a": 1.0}',
    )
    db.add(model)
    db.commit()
    engine.model_runtime.resolve.side_effect = None
    engine.model_runtime.resolve.return_value = {"model_version": model.version, "model": model}
    first = engine.analyze_markets(db, game.id)
    ids = [row.id for row in first]
    model.created_at += timedelta(seconds=1)
    model.notes, model.approved_by = "report", "analyst"
    model.overall_accuracy, model.ats_accuracy, model.games_evaluated = 99, 98, 1000
    model.performance = '{"wins": 100}'
    model.changes = '{ "a": 1, "b": 2.0 }'
    game.game_date += timedelta(hours=1)
    db.commit()
    assert [row.id for row in engine.analyze_markets(db, game.id)] == ids
    model.changes = "Descriptive release note, not runtime configuration"
    game.venue_city, game.venue_state, game.venue_name = "New city", "New state", "New arena"
    game.season, game.neutral_site, game.league = 2030, True, "NBA_PRESEASON"
    db.commit()
    new = engine.analyze_markets(db, game.id)
    assert new[0].id == ids[0]
    engine.simulation_engine = type(engine.simulation_engine)()
    engine.simulation_engine.MARGIN_STANDARD_DEVIATION += 1
    assert engine.analyze_markets(db, game.id)[0].id != new[0].id


@pytest.mark.parametrize("change", [
    "unused_metadata", "home_weight", "spread", "moneyline", "total",
    "runtime_version", "simulation", "moneyline_simulation", "factor_explanation",
    "effective_home_context", "simulation_runs", "factor_order",
])
def test_fixed_seed_outputs_agree_with_effective_input_identity(db, monkeypatch, change):
    game, _, _, engine = seed(db)
    engine.ai_engine = AIAnalysisEngine()
    engine.simulation_engine = SimulationEngine()
    model = ModelVersion(model_name="NBA", sport="NBA", version="NPI-4.0", changes="release notes")
    db.add(model)
    db.commit()
    engine.model_runtime.resolve.side_effect = None
    engine.model_runtime.resolve.return_value = {"model_version": "NPI-4.0", "model": model}

    def preview():
        random.seed(117)
        return [vars(row) for row in engine.analyze_markets(db, game.id, persist=False)]

    before = preview()
    random.seed(117)
    first = engine.analyze_markets(db, game.id)
    fingerprint = first[0].input_fingerprint
    odds = db.query(Odds).one()
    if change == "unused_metadata":
        game.venue_city, game.venue_state, game.venue_name = "City", "State", "Arena"
        game.neutral_site, game.season, game.league = True, 2031, "NBA_PRESEASON"
        model.changes, model.notes, model.games_evaluated = "New release description", "Notes", 100
    elif change == "home_weight":
        engine.npi_engine = NPIEngine(weights={"home_advantage": 10, "historical_rules": 90})
    elif change in {"spread", "moneyline", "total"}:
        field = {"spread": "spread_home", "moneyline": "moneyline_home", "total": "total"}[change]
        setattr(odds, field, getattr(odds, field) + 10)
    elif change == "runtime_version":
        engine.model_runtime.resolve.return_value = {"model_version": "NPI-4.1", "model": model}
    elif change == "simulation":
        engine.simulation_engine.MARGIN_STANDARD_DEVIATION = 18
    elif change == "moneyline_simulation":
        monkeypatch.setattr(SimulationEngine, "MARGIN_STANDARD_DEVIATION", 18)
    elif change == "factor_explanation":
        class ExplainedNPI(NPIEngine):
            def home_advantage(self, game, weight):
                factor = super().home_advantage(game, weight)
                factor.explanation = "Effective home-advantage explanation"
                return factor
        engine.npi_engine = ExplainedNPI()
    elif change == "effective_home_context":
        class ContextualNPI(NPIEngine):
            def home_advantage(self, game, weight):
                factor = super().home_advantage(game, weight)
                factor.score = weight / 2 if game.neutral_site else weight
                return factor
        engine.npi_engine = ContextualNPI()
        game.neutral_site = True
    elif change == "simulation_runs":
        class MoreRuns(SimulationEngine):
            def simulate(self, npi_score, spread, runs=20000):
                return super().simulate(npi_score, spread, runs)
        engine.simulation_engine = MoreRuns()
    else:
        class ReorderedNPI(NPIEngine):
            def calculate(self, *args, **kwargs):
                result = super().calculate(*args, **kwargs)
                result["factors"].reverse()
                return result
        engine.npi_engine = ReorderedNPI()
    db.commit()
    after = preview()
    random.seed(117)
    current = engine.analyze_markets(db, game.id)
    if change == "unused_metadata":
        assert after == before
        assert [row.id for row in current] == [row.id for row in first]
    else:
        # Runtime identity is published provenance even when two profiles have
        # equal default weights and therefore equal fixed-seed outputs.
        if change != "runtime_version":
            assert after != before
        assert current[0].id != first[0].id
        assert current[0].input_fingerprint != fingerprint
    assert [row.id for row in engine.analyze_markets(db, game.id)] == [row.id for row in current]


def test_numeric_and_mapping_fingerprints_are_normalized():
    assert input_fingerprint({"a": 1, "b": {"y": -0.0, "x": 2.0}}) == input_fingerprint({
        "b": {"x": Decimal("2.000"), "y": 0}, "a": 1.0,
    })
    with pytest.raises(ValueError, match="finite"):
        input_fingerprint({"value": float("nan")})
    number = Decimal("123456789012345678901234567890.1250")
    original = input_fingerprint({"value": number})
    with localcontext() as context:
        context.prec = 6
        assert input_fingerprint({"value": number}) == original
    assert input_fingerprint({"value": 10 ** 1000}) != input_fingerprint({"value": 10 ** 1000 + 1})
    assert input_fingerprint({"value": 1}) != input_fingerprint({"value": "1"})
    assert input_fingerprint({"value": 1}) != input_fingerprint({"value": {"number": "1"}})


def test_fingerprint_uses_effective_simulation_default_not_unused_class_setting(db):
    game, _, _, engine = seed(db)
    odds = db.query(Odds).one()
    npi = engine.npi_engine.calculate(game, odds)
    engine.simulation_engine = SimulationEngine()
    original = engine._input_fingerprint(game, odds, "NPI-4.0", {}, npi)
    engine.simulation_engine.DEFAULT_RUNS = 7
    assert engine._input_fingerprint(game, odds, "NPI-4.0", {}, npi) == original

    class DifferentDefaultSimulation(SimulationEngine):
        def simulate(self, npi_score, spread, runs=20000):
            return super().simulate(npi_score, spread, runs)

    engine.simulation_engine = DifferentDefaultSimulation()
    assert engine._input_fingerprint(game, odds, "NPI-4.0", {}, npi) != original


def test_default_analytics_canonical_cross_version_history_retained(db):
    game, _, _, engine = seed(db)
    old = engine.analyze_markets(db, game.id)
    current = engine.analyze_markets(db, game.id, force_regenerate=True)
    old_state = [frozen(row) for row in old]
    for factor in db.query(NPIFactorResult):
        factor.actual_outcome = "HOME" if factor.prediction_id in {p.id for p in current} else "AWAY"
        factor.predicted_side = "HOME"
        if factor.prediction_id in {p.id for p in old}:
            factor.factor_score = 999
    legacy = Prediction(
        **{key: value for key, value in frozen(current[0]).items() if key not in {
            "id", "generation_id", "created_at", "model_version",
        }},
        model_version="NPI-4.0", generation_id=str(uuid4()),
    )
    db.add(legacy)
    db.flush()
    db.add(UserPrediction(user_id=17, prediction_id=old[0].id))
    game.status, game.home_score, game.away_score = "final", 115, 100
    db.commit()
    ResultSettlementService().settle_game(db, game.id)
    factors = ModelEvaluation().factor_summary(db)
    assert all(row["games"] == 1 and row["average_score"] < 999 for row in factors)
    assert all(row["win_rate"] == 100 for row in ModelEvaluation().factor_win_rates(db))
    assert PerformanceEngine().calculate_metrics(db)["total_predictions"] == 3
    intelligence = V1ReadService().get_performance_intelligence(db)
    assert {row["key"]: row["total_bets"] for row in intelligence["by_model_version"]} == {
        "NPI-4.0": 1, "NPI-5.0": 3,
    }
    assert db.query(PredictionResult).count() == 7
    assert [frozen(row) for row in old] == old_state
    assert V1ReadService().get_saved_picks(db, 17)["picks"][0]["prediction_id"] == old[0].id


@pytest.mark.parametrize("market,changed_field", [
    ("spread", "spread_home"), ("spread", "total"),
    ("moneyline", "moneyline_home"), ("moneyline", "total"), ("total", "total"),
])
def test_parlay_newest_matching_observation_preserves_provenance(db, market, changed_field):
    game, _, _, engine = seed(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    original = db.query(Odds).one()
    original.created_at = now - timedelta(hours=8)
    db.commit()
    rows = engine.analyze_markets(db, game.id)
    prediction = next(row for row in rows if row.market == market)
    if market == "moneyline":
        # An otherwise qualified frozen fixture for the freshness-only boundary.
        prediction.selection, prediction.american_odds = "HOME", original.moneyline_home
        prediction.simulation_probability, prediction.projected_edge = 80, 10
        db.commit()
    state = frozen(prediction)
    service = ParlayOptimizerService()
    horizon = now + timedelta(days=7)
    assert not service._load_candidates(db, "NBA", now, horizon)
    fresh = Odds(**{
        name: getattr(original, name) for name in (
            "game_id", "sportsbook", "spread_home", "spread_away",
            "moneyline_home", "moneyline_away", "total",
        )
    }, created_at=now)
    db.add(fresh)
    db.commit()
    candidates = service._load_candidates(db, "NBA", now, horizon)
    assert prediction.id in {row["prediction_id"] for row in candidates}
    mismatched = Odds(**{
        name: getattr(fresh, name) for name in (
            "game_id", "sportsbook", "spread_home", "spread_away",
            "moneyline_home", "moneyline_away", "total", "created_at",
        )
    })
    setattr(mismatched, changed_field, getattr(mismatched, changed_field) + 1)
    db.add(mismatched)
    db.commit()
    assert prediction.id not in {
        row["prediction_id"] for row in service._load_candidates(db, "NBA", now, horizon)
    }
    assert frozen(prediction) == state
    assert db.get(Odds, original.id).created_at == now - timedelta(hours=8)


@contextmanager
def capture_queries(db):
    selects, loaded = [], []
    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)
    def load(_session, instance):
        if isinstance(instance, Prediction):
            loaded.append(instance.id)
    sql_event.listen(db.bind, "before_cursor_execute", capture)
    sql_event.listen(db, "loaded_as_persistent", load)
    try:
        yield selects, loaded
    finally:
        sql_event.remove(db.bind, "before_cursor_execute", capture)
        sql_event.remove(db, "loaded_as_persistent", load)


def test_current_endpoints_bound_rows_and_queries_at_1000_revisions(db):
    game, _, _, engine = seed(db)
    first = engine.analyze_markets(db, game.id)
    game_id = game.id
    template = [frozen(row) for row in first]
    http = client(db)
    counts = {"list": [], "detail": []}
    for size in (1, 10, 100, 1000):
        existing = db.query(Prediction).filter_by(game_id=game_id, market="spread").count()
        mappings = []
        for _ in range(existing, size):
            generation = str(uuid4())
            for row in template:
                mappings.append({
                    **{key: value for key, value in row.items() if key != "id"},
                    "generation_id": generation,
                })
        if mappings:
            db.execute(Prediction.__table__.insert(), mappings)
            db.commit()
        winners = canonical_prediction_ids(db, [game_id])
        for name, path in (("list", "/api/v1/predictions"), ("detail", f"/api/v1/predictions/{game_id}")):
            cache_service.clear()
            db.expunge_all()
            with capture_queries(db) as (selects, loaded):
                response = http.get(path)
            assert response.status_code == 200
            assert {row["prediction_id"] for row in response.json()} == winners
            assert len(loaded) == 3
            counts[name].append(len(selects))
    assert all(len(set(values)) == 1 for values in counts.values())
    print(f"Current endpoints 1/10/100/1000 revisions: SELECTs={counts}, ORM rows=3 each")


def test_current_endpoints_use_semantic_order_not_last_insert(db):
    game, _, _, engine = seed(db)
    current = engine.analyze_markets(db, game.id)
    template = frozen(current[0])
    for version, selection in (("NPI-4.1", "HOME"), ("NPI-5.0", "malformed")):
        db.add(Prediction(**{
            **{key: value for key, value in template.items() if key != "id"},
            "model_version": version, "selection": selection,
            "generation_id": str(uuid4()),
        }))
    db.commit()
    http = client(db)
    for path in ("/api/v1/predictions", f"/api/v1/predictions/{game.id}"):
        cache_service.clear()
        response = http.get(path)
        assert response.status_code == 200
        assert {row["prediction_id"] for row in response.json()} == {row.id for row in current}


def test_regeneration_command_compares_current_rows_when_history_is_protected(db, monkeypatch):
    game, _, _, engine = seed(db)
    old = engine.analyze_markets(db, game.id)
    current = engine.analyze_markets(db, game.id, force_regenerate=True)
    db.add(PredictionResult(
        prediction_id=old[0].id, actual_result="HOME", predicted_result="HOME",
        outcome="WIN", profit_loss=90,
    ))
    db.commit()
    monkeypatch.setattr(regeneration, "PredictionEngine", lambda: engine)
    result = regeneration.regenerate_future_predictions(db, [game.id])
    assert result["results"] == [{
        "game_id": game.id, "status": "protected",
        "prediction_ids": sorted(row.id for row in current),
    }]
    assert db.query(Prediction).count() == 6


@pytest.mark.parametrize("failure", ["analysis", "database"])
def test_regeneration_partial_failure_continues_and_retry_is_idempotent(db, monkeypatch, capsys, failure):
    rows = {"basketball_nba": [event(f"batch-{index}") for index in range(3)]}
    games = importer(db, rows).import_games("NBA")
    engine = prediction_engine()
    ids = [game.id for game in games]
    original_analysis = engine.ai_engine.generate_analysis
    calls = 0

    def fail_mid_market(data):
        nonlocal calls
        calls += 1
        if calls == 5:
            if failure == "database":
                db.execute(text(
                    "INSERT INTO predictions(game_id, market, selection, npi_score, generation_id, input_fingerprint) "
                    "VALUES (:game_id, 'spread', 'HOME', 150, NULL, NULL)"
                ), {"game_id": ids[1]})
            raise RuntimeError("apiKey=must-not-be-disclosed")
        return original_analysis(data)

    engine.ai_engine.generate_analysis = fail_mid_market
    monkeypatch.setattr(regeneration, "PredictionEngine", lambda: engine)
    monkeypatch.setattr(regeneration, "SessionLocal", lambda: db)
    monkeypatch.setattr(sys, "argv", ["refresh", *sum((["--game-id", str(i)] for i in ids), [])])
    assert regeneration.main() == 1
    summary = json.loads(capsys.readouterr().out)
    assert [row["status"] for row in summary["results"]] == ["revised", "failed", "revised"]
    assert summary["counts"] == dict(revised=2, reused=0, protected=0, ineligible=0, no_odds=0, failed=1)
    assert "must-not-be-disclosed" not in json.dumps(summary)
    assert summary["results"][1]["error_type"] == (
        "IntegrityError" if failure == "database" else "RuntimeError"
    )
    assert db.query(Prediction).filter_by(game_id=ids[1]).count() == 0
    assert db.query(AIAnalysis).count() == 6
    assert db.query(NPIFactorResult).count() == 14
    completed = {row.id for row in db.query(Prediction)}
    assert len(completed) == 6
    engine.ai_engine.generate_analysis = original_analysis
    assert regeneration.main() == 0
    retry = json.loads(capsys.readouterr().out)
    assert [row["status"] for row in retry["results"]] == ["reused", "revised", "reused"]
    assert completed <= {row.id for row in db.query(Prediction)}
    assert db.query(Prediction).count() == 9
    assert regeneration.regenerate_future_predictions(db, ids)["counts"]["reused"] == 3
    db.expire_all()
    assert db.query(Prediction).count() == 9


def test_regeneration_missing_odds_continues_and_repaired_retry_reuses_successes(db, monkeypatch):
    events = [event("odds-first"), event("odds-missing", with_odds=False), event("odds-last")]
    service = importer(db, {"basketball_nba": events})
    games = service.import_games("NBA")
    ids = [game.id for game in games]
    engine = prediction_engine()
    monkeypatch.setattr(regeneration, "PredictionEngine", lambda: engine)
    first = regeneration.regenerate_future_predictions(db, ids)
    assert [row["status"] for row in first["results"]] == ["revised", "no_odds", "revised"]
    successes = {row.id for row in db.query(Prediction)}
    source = db.query(Odds).first()
    db.add(Odds(**{
        field: getattr(source, field) for field in (
            "sportsbook", "spread_home", "spread_away", "moneyline_home", "moneyline_away", "total",
        )
    }, game_id=ids[1]))
    db.commit()
    retry = regeneration.regenerate_future_predictions(db, ids)
    assert [row["status"] for row in retry["results"]] == ["reused", "revised", "reused"]
    assert successes <= {row.id for row in db.query(Prediction)}
    assert db.query(Prediction).count() == 9


def test_regeneration_protected_ineligible_and_no_odds_summary(db, monkeypatch, capsys):
    now = datetime.now(timezone.utc)
    events = [
        event("batch-final"), event("batch-started", start=now - timedelta(hours=1)),
        event("batch-no-odds", with_odds=False), event("batch-cancelled"),
    ]
    games = importer(db, {"basketball_nba": events}).import_games("NBA")
    games[0].status, games[3].status = "final", "cancelled"
    db.commit()
    monkeypatch.setattr(regeneration, "PredictionEngine", prediction_engine)
    ids = [game.id for game in games] + [999999]
    summary = regeneration.regenerate_future_predictions(db, ids + ids)
    assert [row["game_id"] for row in summary["results"]] == ids
    assert [row["status"] for row in summary["results"]] == [
        "protected", "protected", "no_odds", "ineligible", "ineligible",
    ]
    assert summary["counts"] == dict(revised=0, reused=0, protected=2, ineligible=2, no_odds=1, failed=0)
    assert db.query(Prediction).count() == 0
    monkeypatch.setattr(regeneration, "SessionLocal", lambda: db)
    monkeypatch.setattr(sys, "argv", ["refresh", "--game-id", str(ids[2])])
    assert regeneration.main() == 1
    assert json.loads(capsys.readouterr().out)["counts"]["no_odds"] == 1


@pytest.mark.parametrize("starting_point", ["prior_heads", "common_ancestor"])
def test_actual_postgres_graph_upgrade_backfill_foreign_keys_and_downgrade(db, starting_point):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Actual production Alembic graph migration requires PostgreSQL")
    rows = {
        "basketball_nba": [event("migration-regular")],
        "basketball_nba_preseason": [event(f"migration-pre-{index}") for index in range(7)],
    }
    games = importer(db, rows).import_games("NBA")
    preseason_game_id = games[-1].id
    if starting_point == "prior_heads":
        ncaaf_game, _, _, _ = seed(db, "NCAAF", "NCAAF")
        games.append(ncaaf_game)
    engine = prediction_engine()
    predictions = [row for game in games for row in engine.analyze_markets(db, game.id)]
    assert sum(row.game_id in {g.id for g in games if g.league == "NBA_PRESEASON"} for row in predictions) == 21
    protected = predictions[0]
    db.add(UserPrediction(user_id=17, prediction_id=protected.id))
    db.add(PredictionLineCorrection(
        prediction_id=protected.id, original_line=protected.line_value,
        corrected_line=protected.line_value, reason="historical fixture",
    ))
    db.add(PredictionResult(
        prediction_id=protected.id, actual_result="HOME", predicted_result="HOME",
        outcome="WIN", profit_loss=90,
    ))
    db.commit()
    originals = {
        row.id: {key: value for key, value in frozen(row).items()
                 if key not in {"generation_id", "input_fingerprint"}}
        for row in predictions
    }
    dependent_counts = {
        table: db.query(table).count()
        for table in (
            UserPrediction, PredictionResult, AIAnalysis, NPIFactorResult,
            PredictionLineCorrection, NcaafRuleIntelligence,
        )
    }
    assert dependent_counts[NcaafRuleIntelligence] == (1 if starting_point == "prior_heads" else 0)
    dependent_rows = {
        table: db.execute(select(table.__table__).order_by(table.id)).mappings().all()
        for table in dependent_counts
    }
    db.expunge_all()
    db.execute(text("DROP INDEX ix_predictions_game_model_market"))
    for name in ("ck_predictions_input_fingerprint", "ck_predictions_generation_id"):
        db.execute(text(f"ALTER TABLE predictions DROP CONSTRAINT {name}"))
    for name in ("input_fingerprint", "generation_id"):
        db.execute(text(f"ALTER TABLE predictions DROP COLUMN {name}"))
    db.execute(text(
        "CREATE UNIQUE INDEX ix_predictions_game_model_market "
        "ON predictions(game_id, model_version, market)"
    ))
    if starting_point == "common_ancestor":
        db.execute(text("DROP TABLE ncaaf_rule_intelligence"))
        command.stamp(alembic_config(db.connection()), "f3a9c7d2e641")
    else:
        command.stamp(alembic_config(db.connection()), ["c6f2a8d4e913", "a4c8e2f19b73"])
    db.commit()
    command.upgrade(alembic_config(db.connection()), "e7b4c2d9a610")
    db.commit()
    assert db.execute(text("SELECT version_num FROM alembic_version")).scalars().all() == ["e7b4c2d9a610"]
    if starting_point == "common_ancestor":
        assert {
            "ncaaf_rule_intelligence", "provider_subscriptions",
            "application_entitlements", "provider_subscription_events",
        } <= set(inspect(db.bind).get_table_names())
    upgraded = db.query(Prediction).order_by(Prediction.id).all()
    backfill = {}
    for row in upgraded:
        expected = str(UUID(hashlib.md5(f"legacy-prediction:{row.id}".encode()).hexdigest()))
        assert row.generation_id == expected
        assert row.input_fingerprint == "unverified:legacy"
        assert {key: value for key, value in frozen(row).items()
                if key not in {"generation_id", "input_fingerprint"}} == originals[row.id]
        backfill[row.id] = row.generation_id
    assert {table: db.query(table).count() for table in dependent_counts} == dependent_counts
    assert {
        table: db.execute(select(table.__table__).order_by(table.id)).mappings().all()
        for table in dependent_counts
    } == dependent_rows
    columns = {row["name"]: row for row in inspect(db.bind).get_columns("predictions")}
    assert not columns["generation_id"]["nullable"] and not columns["input_fingerprint"]["nullable"]
    unique = next(row for row in inspect(db.bind).get_indexes("predictions")
                  if row["name"] == "ix_predictions_game_model_market")
    assert unique["unique"] and unique["column_names"] == [
        "game_id", "model_version", "market", "generation_id",
    ]
    for overrides in ({}, {"generation_id": None}, {"input_fingerprint": None}, {"input_fingerprint": ""}):
        values = {key: value for key, value in frozen(upgraded[0]).items() if key != "id"}
        values.update(overrides)
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(Prediction.__table__.insert().values(**values))
    command.downgrade(alembic_config(db.connection()), "c6f2a8d4e913")
    db.commit()
    assert set(db.execute(text("SELECT version_num FROM alembic_version")).scalars()) == {
        "c6f2a8d4e913", "a4c8e2f19b73",
    }
    command.upgrade(alembic_config(db.connection()), "e7b4c2d9a610")
    db.commit()
    db.expunge_all()
    assert {row.id: row.generation_id for row in db.query(Prediction)} == backfill
    refreshed = engine.analyze_markets(db, preseason_game_id)
    assert all(row.input_fingerprint != "unverified:legacy" for row in refreshed)
    with pytest.raises(RuntimeError, match="without losing history"):
        command.downgrade(alembic_config(db.connection()), "c6f2a8d4e913")
    db.rollback()
    assert db.execute(text("SELECT version_num FROM alembic_version")).scalar() == "e7b4c2d9a610"
    assert db.query(Prediction).count() == len(originals) + 3
