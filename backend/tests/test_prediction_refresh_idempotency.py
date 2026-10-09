from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
from uuid import uuid4
from threading import Barrier

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, event as sql_event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.game import Game
from app.models.model_registry import ModelRegistry
from app.models.model_version import ModelVersion
from app.models.ncaaf_rule_intelligence import NcaafRuleIntelligence
from app.models.npi_factor_result import NPIFactorResult
from app.models.npi_weight_profile import NPIWeightProfile
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.team_performance import TeamPerformance
from app.models.prediction_line_correction import PredictionLineCorrection
from app.models.user_prediction import UserPrediction
from app.services.npi_weight_profile_service import NPIWeightProfileService
from app.services.prediction_engine import PredictionEngine
from app.services.prediction_publication import canonical_prediction_ids
from app.services.result_settlement_service import ResultSettlementService
from app.services.user_prediction_service import save_prediction
from app.workers import upcoming_game_worker
from test_nba_preseason_sync import event, importer, prediction_engine


@pytest.fixture(params=["sqlite", "postgres"])
def db(request):
    if request.param == "postgres":
        target = os.environ.get("METRIC_TEST_POSTGRES_URL")
        if not target:
            pytest.skip("Disposable PostgreSQL URL not supplied")
        url = make_url(target)
        assert url.get_backend_name() == "postgresql"
        assert url.host in {"127.0.0.1", "localhost"}
        assert url.database == "metric_integrity_test"
        schema = f"refresh_{uuid4().hex}"
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        tables = [
            Team.__table__, Game.__table__, Odds.__table__, Prediction.__table__,
            PredictionResult.__table__, AIAnalysis.__table__, NPIFactorResult.__table__,
            NPIWeightProfile.__table__, ModelRegistry.__table__, ModelVersion.__table__,
            NcaafRuleIntelligence.__table__, UserPrediction.__table__,
            TeamPerformance.__table__, PredictionLineCorrection.__table__,
        ]
        Base.metadata.create_all(engine, tables=tables)
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO users (id) VALUES (17)"))
        with sessionmaker(bind=engine)() as session:
            yield session
    finally:
        engine.dispose()
        if request.param == "postgres":
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


SPORTS = [
    ("NFL", "NFL"), ("NBA", "basketball_nba"),
    ("NBA", "basketball_nba_preseason"), ("NCAAF", "NCAAF"),
    ("NCAAB", "NCAAB"), ("WNBA", "WNBA"),
]


def seed(db, sport="NBA", source="basketball_nba"):
    rows = {source: [event(f"{source}-refresh")]}
    service = importer(db, rows)
    game = service.import_games(sport)[0]
    return game, service, rows, prediction_engine()


def frozen(row):
    return {column.name: getattr(row, column.name) for column in Prediction.__table__.columns}


@pytest.mark.parametrize("sport,source", SPORTS)
def test_two_worker_syncs_are_idempotent_for_every_sport(db, monkeypatch, sport, source):
    rows = {source: [event(f"{source}-worker")]}
    service = importer(db, rows)
    engine = prediction_engine()
    monkeypatch.setattr(upcoming_game_worker, "_configured_sports", lambda: [sport])
    monkeypatch.setattr(upcoming_game_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", lambda **kwargs: service)
    monkeypatch.setattr(upcoming_game_worker, "PredictionEngine", lambda: engine)
    first = upcoming_game_worker.run_once()[sport]
    ids = [row.id for row in db.query(Prediction).order_by(Prediction.id)]
    second = upcoming_game_worker.run_once()[sport]
    assert first["prediction_errors"] == second["prediction_errors"] == 0
    assert first["predictions_generated"] == second["predictions_generated"] == 3
    assert [row.id for row in db.query(Prediction).order_by(Prediction.id)] == ids
    assert db.query(Prediction).count() == 3
    assert db.query(Odds).count() == 1


@pytest.mark.parametrize("sport,source", SPORTS)
def test_changed_odds_publish_new_immutable_revision(db, sport, source):
    game, service, rows, engine = seed(db, sport, source)
    first = engine.analyze_markets(db, game.id)
    original = [frozen(row) for row in first]
    for outcome in rows[source][0]["bookmakers"][0]["markets"][2]["outcomes"]:
        outcome["point"] = 220.5
    service.import_games(sport)
    refreshed = engine.analyze_markets(db, game.id)
    assert [row.id for row in refreshed] != [row.id for row in first]
    assert next(row.line_value for row in refreshed if row.market == "total") == 220.5
    assert all(row.odds_snapshot_id == db.query(Odds.id).order_by(Odds.id.desc()).first()[0]
               for row in refreshed)
    assert [frozen(row) for row in first] == original
    assert canonical_prediction_ids(db, [game.id]) == {row.id for row in refreshed}
    assert db.query(Prediction).count() == 6


def test_current_profile_model_and_game_inputs_invalidate_same_snapshot(db):
    game, _, _, engine = seed(db)
    profiles = NPIWeightProfileService()
    profiles.create_profile(db, "NBA", "NPI-4.0", engine.npi_engine.DEFAULT_WEIGHTS)
    first = engine.analyze_markets(db, game.id)
    first_frozen = [frozen(row) for row in first]
    profiles.create_profile(db, "NBA", "NPI-4.0", {
        "home_advantage": 10, "spread_value": 20, "market_environment": 10,
        "situational_edge": 10, "historical_rules": 150,
    })
    changed = engine.analyze_markets(db, game.id)
    assert changed[0].npi_score != first[0].npi_score
    assert changed[0].odds_snapshot_id == first[0].odds_snapshot_id
    engine.model_runtime = PredictionEngine.model_runtime
    model = ModelVersion(model_name="NBA", sport="NBA", version="NPI-4.1", status="production")
    db.add(model)
    registry = ModelRegistry(
        model_name="NBA", sport="NBA", version="4.1", model_version="NPI-4.1",
        is_active=True, production_status=True,
    )
    db.add(registry)
    db.commit()
    active = engine.analyze_markets(db, game.id)
    assert active[0].id != changed[0].id
    model.changes = '{"material_configuration":"new"}'
    db.commit()
    configured = engine.analyze_markets(db, game.id)
    assert configured[0].id == active[0].id
    game.neutral_site = True
    db.commit()
    current = engine.analyze_markets(db, game.id)
    assert current[0].id == configured[0].id
    assert [row.id for row in engine.analyze_markets(db, game.id)] == [row.id for row in current]
    assert [frozen(row) for row in first] == first_frozen


def test_saved_picks_analyses_factors_and_publication_history_survive_refresh(db):
    game, service, rows, engine = seed(db)
    first = engine.analyze_markets(db, game.id)
    original = [frozen(row) for row in first]
    save_prediction(db, 17, first[0].id)
    analysis_ids = [row.id for row in db.query(AIAnalysis)]
    factor_ids = [row.id for row in db.query(NPIFactorResult)]
    for outcome in rows["basketball_nba"][0]["bookmakers"][0]["markets"][2]["outcomes"]:
        outcome["point"] = 230.5
    service.import_games("NBA")
    current = engine.analyze_markets(db, game.id)
    assert current[0].id != first[0].id
    assert db.query(UserPrediction).one().prediction_id == first[0].id
    assert [frozen(row) for row in first] == original
    assert set(analysis_ids) <= {row.id for row in db.query(AIAnalysis)}
    assert set(factor_ids) <= {row.id for row in db.query(NPIFactorResult)}
    assert canonical_prediction_ids(db, [game.id]) == {row.id for row in current}


def test_settled_predictions_are_immutable_even_when_forced(db):
    game, _, _, engine = seed(db)
    first = engine.analyze_markets(db, game.id)
    game.status = "final"
    game.home_score, game.away_score = 115, 100
    db.commit()
    ResultSettlementService().settle_game(db, game.id)
    original = [frozen(row) for row in first]
    result_ids = {row.id for row in db.query(PredictionResult)}
    current = engine.analyze_markets(db, game.id, force_regenerate=True)
    assert [frozen(row) for row in current] == original
    assert {row.id for row in db.query(PredictionResult)} == result_ids
    assert db.query(Prediction).count() == 3


def test_nba_phases_coexist_and_input_reversion_does_not_resurrect_history(db):
    rows = {
        "basketball_nba": [event("regular-revision")],
        "basketball_nba_preseason": [event("preseason-revision")],
    }
    games = importer(db, rows).import_games("NBA")
    engine = prediction_engine()
    for game in games:
        first = engine.analyze_markets(db, game.id)
        odds = db.get(Odds, first[0].odds_snapshot_id)
        old_total = odds.total
        odds.total = old_total + 5
        db.commit()
        second = engine.analyze_markets(db, game.id)
        odds.total = old_total
        db.commit()
        third = engine.analyze_markets(db, game.id)
        assert first[0].input_fingerprint == third[0].input_fingerprint
        assert first[0].id < second[0].id < third[0].id
    assert {game.league for game in games} == {"NBA", "NBA_PRESEASON"}
    assert db.query(Prediction).count() == 18


def test_publication_rolls_back_all_markets_and_dependents_on_failure(db):
    game, _, _, engine = seed(db, "NCAAF", "NCAAF")
    original = engine.ai_engine.generate_analysis.side_effect
    calls = 0
    def fail_second(data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("Injected analysis failure")
        return {"engine_version": "test", "summary": "test", "explanation": "test"}
    engine.ai_engine.generate_analysis.side_effect = fail_second
    with pytest.raises(RuntimeError, match="Injected analysis failure"):
        engine.analyze_markets(db, game.id)
    for table in [Prediction, AIAnalysis, NPIFactorResult, NcaafRuleIntelligence]:
        assert db.query(table).count() == 0
    engine.ai_engine.generate_analysis.side_effect = original
    assert len(engine.analyze_markets(db, game.id)) == 3


def test_lookup_count_and_prediction_materialization_do_not_grow_with_history(db):
    game, _, _, engine = seed(db)
    counts = []
    for history_size in [1, 10, 100]:
        while db.query(Prediction).filter_by(game_id=game.id, market="spread").count() < history_size:
            engine.analyze_markets(db, game.id, force_regenerate=True)
        db.expunge_all()
        queries, loaded = [], []
        def capture(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().upper().startswith("SELECT"):
                queries.append(statement)
        def load(session, instance):
            if isinstance(instance, Prediction):
                loaded.append(instance.id)
        sql_event.listen(db.bind, "before_cursor_execute", capture)
        sql_event.listen(db, "loaded_as_persistent", load)
        try:
            result = engine.analyze_markets(db, game.id)
        finally:
            sql_event.remove(db.bind, "before_cursor_execute", capture)
            sql_event.remove(db, "loaded_as_persistent", load)
        assert len(result) == 3
        assert len(loaded) == 3
        counts.append(len(queries))
    assert len(set(counts)) == 1
    print(f"History sizes 1/10/100: SELECT counts={counts}; Prediction ORM rows=3/3/3")


def test_real_old_constraint_reproduction_and_migration_preserves_history(db):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("Production migration uses PostgreSQL deterministic backfill")
    migration_path = Path(__file__).parents[1] / "migrations" / "versions" / "c8d2f6a109b4_add_prediction_refresh_revisions.py"
    spec = importlib.util.spec_from_file_location("revision_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    connection = db.connection()
    connection.execute(text("DROP INDEX ix_predictions_game_model_market"))
    connection.execute(text("ALTER TABLE predictions DROP CONSTRAINT ck_predictions_input_fingerprint"))
    connection.execute(text("ALTER TABLE predictions DROP CONSTRAINT ck_predictions_generation_id"))
    connection.execute(text("ALTER TABLE predictions DROP COLUMN input_fingerprint"))
    connection.execute(text("ALTER TABLE predictions DROP COLUMN generation_id"))
    connection.execute(text(
        "CREATE UNIQUE INDEX ix_predictions_game_model_market "
        "ON predictions(game_id, model_version, market)"
    ))
    # Exercise precisely the migrated production index, not just Base metadata.
    insert = text(
        "INSERT INTO predictions(game_id, model_version, market, selection, npi_score) "
        "VALUES (:game_id, 'NPI-5.0', 'spread', 'HOME', 150)"
    )
    game, _, _, engine = seed(db)
    db.execute(insert, {"game_id": game.id})
    db.commit()
    with pytest.raises(IntegrityError):
        db.execute(insert, {"game_id": game.id})
    db.rollback()
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.upgrade()
    db.commit()
    old = db.query(Prediction).one()
    original = frozen(old)
    current = engine.analyze_markets(db, game.id)
    assert [row.id for row in engine.analyze_markets(db, game.id)] == [row.id for row in current]
    assert frozen(old) == original
    assert db.query(Prediction).count() == 4
    indexes = inspect(db.bind).get_indexes("predictions")
    index = next(row for row in indexes if row["name"] == "ix_predictions_game_model_market")
    assert index["unique"]
    assert index["column_names"] == ["game_id", "model_version", "market", "generation_id"]
    with Operations.context(MigrationContext.configure(db.connection())):
        with pytest.raises(RuntimeError, match="without losing history"):
            migration.downgrade()


def test_production_generation_path_reproduces_old_key_and_new_key_rejects_duplicate_market(db):
    game, service, rows, engine = seed(db)
    db.execute(text("DROP INDEX ix_predictions_game_model_market"))
    db.execute(text(
        "CREATE UNIQUE INDEX ix_predictions_game_model_market "
        "ON predictions(game_id, model_version, market)"
    ))
    db.commit()
    first = engine.analyze_markets(db, game.id)
    original = [frozen(row) for row in first]
    for outcome in rows["basketball_nba"][0]["bookmakers"][0]["markets"][2]["outcomes"]:
        outcome["point"] = 230.5
    service.import_games("NBA")
    with pytest.raises(IntegrityError):
        engine.analyze_markets(db, game.id)
    assert db.query(Prediction).count() == 3
    assert [frozen(row) for row in first] == original
    db.execute(text("DROP INDEX ix_predictions_game_model_market"))
    db.execute(text(
        "CREATE UNIQUE INDEX ix_predictions_game_model_market "
        "ON predictions(game_id, model_version, market, generation_id)"
    ))
    db.commit()
    refreshed = engine.analyze_markets(db, game.id)
    assert db.query(Prediction).count() == 6
    with pytest.raises(IntegrityError):
        db.execute(text(
            "INSERT INTO predictions(game_id, model_version, market, selection, npi_score, generation_id, input_fingerprint) "
            "VALUES (:game_id, 'NPI-5.0', 'spread', 'HOME', 150, :generation_id, :fingerprint)"
        ), {
            "game_id": game.id, "generation_id": refreshed[0].generation_id,
            "fingerprint": refreshed[0].input_fingerprint,
        })
    db.rollback()
    assert db.query(Prediction).count() == 6


def test_concurrent_postgres_refresh_serializes_and_reuses_one_publication(db):
    if db.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock concurrency test")
    game, _, _, _ = seed(db)
    game_id = game.id
    factory = sessionmaker(bind=db.bind)
    barrier = Barrier(2)
    def refresh():
        with factory() as session:
            barrier.wait(timeout=10)
            return [row.id for row in prediction_engine().analyze_markets(session, game_id)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: refresh(), range(2)))
    assert first == second
    assert db.query(Prediction).count() == 3
