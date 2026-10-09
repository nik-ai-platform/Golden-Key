import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from unittest.mock import Mock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from test_final_score_settlement_service import FakeScoreClient, _session

from app.database.base import Base
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.odds import Odds
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.models.team_provider_identity import TeamProviderIdentity
from app.repositories.odds_repository import SNAPSHOT_FIELDS
from app.services.final_score_settlement_service import FinalScoreSettlementService
from app.services.odds_importer import OddsImporter
from app.services.odds_normalizer_service import OddsNormalizerService
from app.services.paired_market_prices import paired_market_prices_with_diagnostics
from app.services.odds_service import OddsService, create_odds_snapshot
from scripts.report_odds_capture_coverage import build_report


@pytest.fixture(params=["sqlite", "postgres"])
def capture_db(request):
    if request.param == "postgres":
        target = os.environ.get("METRIC_TEST_POSTGRES_URL")
        if not target:
            pytest.skip("Disposable PostgreSQL URL not supplied")
        url = make_url(target)
        assert url.host in {"127.0.0.1", "localhost"} and url.database == "metric_integrity_test"
        schema = "capture_" + uuid4().hex
        admin = create_engine(url)
        with admin.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
        )
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE import_runs (id INTEGER PRIMARY KEY)"))
        Base.metadata.create_all(engine, tables=[
            Team.__table__, Game.__table__, Odds.__table__, GameResultObservation.__table__,
            TeamAlias.__table__, TeamProviderIdentity.__table__,
        ])
        with sessionmaker(bind=engine)() as db:
            yield db
    finally:
        engine.dispose()
        if request.param == "postgres":
            with admin.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def seed(db):
    home, away = Team(name="Home", sport="WNBA", league="WNBA"), Team(name="Away", sport="WNBA", league="WNBA")
    db.add_all([home, away])
    db.flush()
    game = Game(
        home_team_id=home.id, away_team_id=away.id, provider_game_id="live-capture",
        sport="WNBA", league="WNBA", game_date=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
    )
    db.add(game)
    db.commit()
    return game


def quote():
    return {"title": "Book", "markets": [
        {"key": "spreads", "outcomes": [
            {"name": "Away", "point": 4.5, "price": 105},
            {"name": "Home", "point": -4.5, "price": -125},
        ]},
        {"key": "totals", "outcomes": [
            {"name": "Under", "point": 170.5, "price": -115},
            {"name": "Over", "point": 170.5, "price": -105},
        ]},
        {"key": "h2h", "outcomes": [
            {"name": "Away", "price": 155}, {"name": "Home", "price": -180},
        ]},
    ]}


def final(home=90, away=80, **extra):
    return {
        "id": "live-capture", "completed": True, "home_team": "Home", "away_team": "Away",
        "scores": [{"name": "Away", "score": away}, {"name": "Home", "score": home}],
        **extra,
    }


def service(rows):
    return FinalScoreSettlementService(
        provider_client=FakeScoreClient(rows),
        settlement_service=Mock(settle_game=Mock(return_value={"settled": 0})),
    )


@pytest.mark.parametrize("path", ["normalized", "worker"])
def test_prices_survive_import_and_changed_quotes_append(capture_db, path):
    db = capture_db
    game = seed(db)
    bookmaker = quote()

    def save():
        if path == "worker":
            return create_odds_snapshot(db, game.id, bookmaker, monitor=Mock())
        values = OddsNormalizerService().normalize_bookmaker(
            {"home_team": "Home", "away_team": "Away"}, bookmaker,
        )
        return OddsImporter().import_odds(db, [{"game_id": game.id, **values}])[0]

    first = save()
    original = {name: getattr(first, name) for name in SNAPSHOT_FIELDS}
    assert (first.spread_home_price, first.spread_away_price) == (-125, 105)
    assert (first.total_over_price, first.total_under_price) == (-105, -115)
    assert (first.moneyline_home, first.moneyline_away) == (-180, 155)
    assert save().id == first.id
    bookmaker["markets"][0]["outcomes"][0]["price"] = 110
    second = save()
    assert second.id != first.id and second.spread_away_price == 110
    bookmaker["markets"][0]["outcomes"][0]["price"] = 105
    reverted = save()
    assert reverted.id not in {first.id, second.id}
    assert db.query(Odds).count() == 3
    db.refresh(first)
    assert original == {name: getattr(first, name) for name in SNAPSHOT_FIELDS}
    bookmaker["title"] = "Other book"
    assert save().id != reverted.id


def test_capture_diagnostics_count_pair_success_and_rejection_reason():
    bookmaker = quote()
    prices, diagnostics = paired_market_prices_with_diagnostics(
        bookmaker,
        "Home",
        "Away",
        spread_home=-4.5,
        spread_away=4.5,
        total=170.5,
    )
    assert prices["spread_home_price"] == -125
    assert prices["spread_away_price"] == 105
    assert diagnostics == {
        "spread_pair_captured": 1,
        "total_pair_captured": 1,
    }

    bookmaker["markets"][0]["outcomes"][0]["point"] = 5.5
    prices, diagnostics = paired_market_prices_with_diagnostics(
        bookmaker,
        "Home",
        "Away",
        spread_home=-4.5,
        spread_away=4.5,
        total=170.5,
    )
    assert prices["spread_home_price"] is None
    assert diagnostics["spread_line_mismatch"] == 1
    assert diagnostics["total_pair_captured"] == 1


def test_odds_snapshot_collector_accumulates_market_diagnostics(capture_db):
    game = seed(capture_db)
    diagnostics = {}

    snapshot = create_odds_snapshot(
        capture_db,
        game.id,
        quote(),
        monitor=Mock(),
        price_capture_diagnostics=diagnostics,
    )

    assert snapshot is not None
    assert diagnostics == {
        "spread_pair_captured": 1,
        "total_pair_captured": 1,
    }


def test_coverage_report_includes_quote_identity_and_explicit_site_status(capture_db):
    game = seed(capture_db)
    game.venue_name = "Neutral Arena"
    home = capture_db.get(Team, game.home_team_id)
    capture_db.add(
        TeamProviderIdentity(
            team_id=home.id,
            provider="odds_api",
            sport="WNBA",
            provider_team_id="home-id",
            provider_name=home.name,
        )
    )
    capture_db.add(
        TeamAlias(
            team_id=home.id,
            provider="odds_api",
            alias_name="Home Alias",
            normalized_alias="homealias",
        )
    )
    capture_db.add_all(
        [
            Odds(
                game_id=game.id,
                sportsbook="Paired",
                spread_home=-4.5,
                spread_away=4.5,
                spread_home_price=-110,
                spread_away_price=105,
                total=170.5,
                total_over_price=-105,
                total_under_price=-115,
                created_at=datetime(2026, 10, 1, 10),
            ),
            Odds(
                game_id=game.id,
                sportsbook="Legacy",
                spread_home=-4.5,
                spread_away=4.5,
                total=170.5,
                created_at=datetime(2026, 10, 1, 11),
            ),
        ]
    )
    capture_db.commit()

    report = build_report(capture_db)
    row = next(sport for sport in report["sports"] if sport["sport"] == "WNBA")

    assert report["read_only"] is True
    assert row["spread"] == {
        "quote_snapshots": 2,
        "complementary_line_snapshots": 2,
        "paired_price_snapshots": 1,
        "one_price_missing_or_invalid": 0,
        "both_prices_missing_or_invalid": 1,
        "noncomplementary_line_snapshots": 0,
    }
    assert row["spread_since_first_paired_capture"][
        "quote_snapshots_since_first_pair"
    ] == 2
    assert row["spread_since_first_paired_capture"][
        "paired_price_snapshots_since_first_pair"
    ] == 1
    assert row["neutral_site_unknown"] == 1
    assert row["games_with_explicit_venue"] == 1
    assert row["team_ids_with_matching_sport_provider_identity"] == 1
    assert row["team_ids_with_alias"] == 1


@pytest.mark.parametrize("change", ["spread", "total", "missing", "invalid", "duplicate"])
def test_mismatched_or_invalid_pairs_keep_lines_but_no_prices(change):
    bookmaker = quote()
    if change == "spread":
        bookmaker["markets"][0]["outcomes"][0]["point"] = 5.5
    elif change == "total":
        bookmaker["markets"][1]["outcomes"][0]["point"] = 171.5
    elif change == "missing":
        bookmaker["markets"][0]["outcomes"][0].pop("price")
        bookmaker["markets"][1]["outcomes"][0].pop("price")
    elif change == "invalid":
        bookmaker["markets"][0]["outcomes"][0]["price"] = float("nan")
        bookmaker["markets"][1]["outcomes"][0]["price"] = True
    else:
        bookmaker["markets"][0]["outcomes"].append(dict(bookmaker["markets"][0]["outcomes"][0]))
        bookmaker["markets"][1]["outcomes"].append(dict(bookmaker["markets"][1]["outcomes"][0]))
    result = OddsNormalizerService().normalize_bookmaker(
        {"home_team": "Home", "away_team": "Away"}, bookmaker,
    )
    assert result["spread_home"] == -4.5 and result["total"] == 170.5
    assert (result["moneyline_home"], result["moneyline_away"]) == (-180, 155)
    if change != "total":
        assert result["spread_home_price"] is result["spread_away_price"] is None
    if change != "spread":
        assert result["total_over_price"] is result["total_under_price"] is None
    assert OddsService().extract_market_values(bookmaker, "Home", "Away") == (
        -4.5, 5.5 if change == "spread" else 4.5, -180, 155,
        171.5 if change == "total" else 170.5,
    )


def test_final_receipts_idempotent_corrections_and_reversions(capture_db):
    db = capture_db
    game = seed(db)
    old_update = "2020-01-01T03:00:00+03:00"
    sync = service([final(last_update=old_update)])
    before = datetime.now(UTC).replace(tzinfo=None)
    assert sync.sync_sport(db, "WNBA").errors == 0
    first = db.query(GameResultObservation).one()
    assert before <= first.observed_at <= datetime.now(UTC).replace(tzinfo=None)
    assert first.source_updated_at == datetime(2020, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    sync.provider_client.rows = [final(last_update="2026-10-08T01:00:00Z")]
    sync.sync_sport(db, "WNBA")
    assert db.query(GameResultObservation).count() == 1
    sync.provider_client.rows = [final(home=70)]
    sync.sync_sport(db, "WNBA")
    sync.provider_client.rows = [final()]
    sync.sync_sport(db, "WNBA")
    rows = db.query(GameResultObservation).order_by(GameResultObservation.id).all()
    assert [r.home_score for r in rows] == [90, 70, 90]
    assert rows[0].observed_at <= rows[1].observed_at <= rows[2].observed_at
    assert rows[0].source_updated_at == datetime(2020, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    db.refresh(game)
    assert (game.status, game.home_score, game.away_score) == ("final", 90, 80)


@pytest.mark.parametrize("value", [-1, None, "bad", float("inf"), float("nan"), True, 90.5])
def test_invalid_finals_create_no_observations(capture_db, value):
    db = capture_db
    game = seed(db)
    summary = service([final(home=value)]).sync_sport(db, "WNBA")
    assert summary.errors == 1
    assert db.query(GameResultObservation).count() == 0
    db.refresh(game)
    assert game.status == "scheduled" and game.home_score is None


def test_incomplete_final_and_invalid_metadata(capture_db, caplog):
    db = capture_db
    seed(db)
    service([final(completed=False)]).sync_sport(db, "WNBA")
    assert db.query(GameResultObservation).count() == 0
    service([final(last_update="not-a-date")]).sync_sport(db, "WNBA")
    assert db.query(GameResultObservation).one().source_updated_at is None
    assert "Invalid final score source timestamp" in caplog.text


def test_observation_and_scores_roll_back_together(capture_db):
    db = capture_db
    game = seed(db)

    def fail_insert(mapper, connection, target):
        raise RuntimeError("Synthetic observation persistence failure")

    event.listen(GameResultObservation, "before_insert", fail_insert)
    try:
        assert service([final()]).sync_sport(db, "WNBA").errors == 1
    finally:
        event.remove(GameResultObservation, "before_insert", fail_insert)
    db.refresh(game)
    assert game.status == "scheduled" and game.home_score is None
    assert db.query(GameResultObservation).count() == 0


@pytest.mark.parametrize("field", SNAPSHOT_FIELDS)
def test_each_changed_field_appends_and_unchanged_reuses(capture_db, field):
    db = capture_db
    game = seed(db)
    values = {
        "game_id": game.id,
        **OddsNormalizerService().normalize_bookmaker(
            {"home_team": "Home", "away_team": "Away"}, quote(),
        ),
    }
    importer = OddsImporter()
    first = importer.import_odds(db, [values])[0]
    changed = {**values, field: values[field] + 1}
    second = importer.import_odds(db, [changed])[0]
    assert second.id != first.id
    assert importer.import_odds(db, [changed])[0].id == second.id
    db.refresh(first)
    assert getattr(first, field) == values[field]
    assert db.query(Odds).count() == 2


@pytest.mark.parametrize("kind", ["final", "odds"])
def test_concurrent_polling_serializes_duplicate_capture(capture_db, kind):
    db = capture_db
    if db.bind.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock test")
    game_id = seed(db).id
    factory = sessionmaker(bind=db.bind)
    barrier = Barrier(2)

    def poll():
        with factory() as session:
            barrier.wait(timeout=10)
            if kind == "final":
                assert service([final()]).sync_sport(session, "WNBA").errors == 0
            else:
                create_odds_snapshot(session, game_id, quote(), monitor=Mock())

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: poll(), range(2)))
    assert db.query(GameResultObservation if kind == "final" else Odds).count() == 1


def test_price_migration_preserves_legacy_rows_and_downgrades(capture_db):
    db = capture_db
    game = seed(db)
    db.add(Odds(game_id=game.id, sportsbook="Legacy", spread_home=-4.5, total=170.5))
    db.commit()
    migration = importlib.import_module("migrations.versions.b0c3f5e8d142_capture_paired_market_prices")
    with db.bind.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
            migration.upgrade()
        legacy = connection.execute(text(
            "SELECT spread_home, total, spread_home_price, spread_away_price, "
            "total_over_price, total_under_price FROM odds"
        )).one()
        assert tuple(legacy) == (-4.5, 170.5, None, None, None, None)
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert not set(migration.PRICE_COLUMNS) & {c["name"] for c in inspect(connection).get_columns("odds")}
        assert connection.execute(text("SELECT count(*) FROM odds")).scalar_one() == 1


def test_live_correction_does_not_regrade_settled_pick():
    from app.models.prediction_record import Prediction

    with _session() as db:
        game = seed(db)
        db.add(Prediction(
            game_id=game.id, market="moneyline", selection="HOME",
            american_odds=-180, model_version="NPI-5.0", npi_score=100,
        ))
        db.commit()
        provider = FakeScoreClient([final()])
        sync = FinalScoreSettlementService(provider_client=provider)
        sync.sync_sport(db, "WNBA")
        result = db.query(PredictionResult).one()
        old = (result.id, result.outcome, result.profit_loss)
        provider.rows = [final(home=70)]
        sync.sync_sport(db, "WNBA")
        db.refresh(result)
        assert (result.id, result.outcome, result.profit_loss) == old
        assert result.outcome == "WIN"
        assert db.query(GameResultObservation).count() == 2
