from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.nik_score import NikScore
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.prediction_outcome import PredictionOutcome
from app.models.user_prediction import UserPrediction
from app.repositories import analytics_repository
from app.services.analytics.confidence_service import ConfidenceService
from app.services.calibration_service import CalibrationService
from app.services.final_score_settlement_service import FinalScoreSettlementService
from app.services.live_data_service import LiveDataService
from app.services.odds_provider_client import OddsProviderClient
from app.services.performance_engine import PerformanceEngine
from app.services.prediction_engine import PredictionEngine
from app.services.npi_weight_profile_service import NPIWeightProfileService
from app.scheduler.job_scheduler import JobScheduler
import requests
from app.services.prediction_outcome_service import PredictionOutcomeService
from app.services.sport_mapping_service import NBA_PRESEASON, SportMappingService
from app.services.v1_read_service import V1ReadService
from app.workers import upcoming_game_worker
from app.workers.game_importer import GameOddsImporter


KEYS = ("basketball_nba", "basketball_nba_preseason")


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def event(event_id, *, with_odds=True, start=None):
    start = start or datetime.now(timezone.utc) + timedelta(days=1)
    row = {
        "id": event_id,
        "home_team": "Boston Celtics",
        "away_team": "New York Knicks",
        "commence_time": start.isoformat(),
        "bookmakers": [],
    }
    if with_odds:
        row["bookmakers"] = [{
            "title": "Test Sportsbook",
            "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": row["away_team"], "price": 230},
                    {"name": row["home_team"], "price": -280},
                ]},
                {"key": "spreads", "outcomes": [
                    {"name": row["away_team"], "point": 7.5},
                    {"name": row["home_team"], "point": -7.5},
                ]},
                {"key": "totals", "outcomes": [
                    {"name": "Over", "point": 212.5},
                    {"name": "Under", "point": 212.5},
                ]},
            ],
        }]
    return row


def importer(db, rows):
    live = MagicMock()
    live.fetch_games.side_effect = lambda key: deepcopy(rows.get(key, []))
    return GameOddsImporter(db, live_data_service=live)


def prediction_engine():
    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError("No production model configured for sport: NBA")
    engine.ai_engine = MagicMock(VERSION="test")
    engine.ai_engine.generate_analysis.return_value = {
        "engine_version": "test", "summary": "Test analysis", "explanation": "Test analysis",
    }
    return engine


def final(row):
    return {
        **row, "completed": True,
        "scores": [
            {"name": row["away_team"], "score": "100"},
            {"name": row["home_team"], "score": "115"},
        ],
    }


def test_nba_competition_mapping_is_explicit():
    sources = SportMappingService().competition_sources(" nba ")
    assert [(s.provider_key, s.league) for s in sources] == [
        (KEYS[0], "NBA"), (KEYS[1], NBA_PRESEASON),
    ]


@pytest.mark.parametrize("sport,key", [
    ("NFL", "americanfootball_nfl"), ("NCAAF", "americanfootball_ncaaf"),
    ("NCAAB", "basketball_ncaab"), ("WNBA", "basketball_wnba"),
])
def test_other_sports_keep_one_source(db, sport, key):
    service = importer(db, {})
    assert service.import_games(sport) == []
    service.live_data.fetch_games.assert_called_once_with(sport)
    assert [(s.provider_key, s.league) for s in service.sport_mapping.competition_sources(sport)] == [
        (key, sport),
    ]


def test_requests_use_both_exact_odds_and_score_urls(db, monkeypatch):
    response = MagicMock()
    response.json.return_value = []
    request = MagicMock(return_value=response)
    monkeypatch.setattr("requests.get", request)
    GameOddsImporter(db, live_data_service=LiveDataService()).import_games("NBA")
    assert [call.args[0] for call in request.call_args_list] == [
        f"{LiveDataService.BASE_URL}/{key}/odds" for key in KEYS
    ]
    for call in request.call_args_list:
        assert call.kwargs["params"]["markets"] == "h2h,spreads,totals"
        assert call.kwargs["params"]["regions"] == "us"
        assert call.kwargs["params"]["oddsFormat"] == "american"
    request.reset_mock()
    client = OddsProviderClient()
    FinalScoreSettlementService(provider_client=client).sync_sport(db, "NBA", days_from=2)
    assert [call.args[0] for call in request.call_args_list] == [
        f"{client.base_url}/sports/{key}/scores/" for key in KEYS
    ]
    assert all(call.kwargs["params"]["daysFrom"] == 2 for call in request.call_args_list)


def test_import_normalizes_phase_exact_ids_refresh_counts_and_odds(db):
    service = importer(db, {KEYS[0]: [event("regular")], KEYS[1]: [event("preseason")]})
    first = service.import_games("NBA")
    assert len(first) == 2
    assert {g.sport for g in first} == {"NBA"}
    assert {g.provider_game_id: g.league for g in first} == {
        "regular": "NBA", "preseason": NBA_PRESEASON,
    }
    original_ids = [g.id for g in first]
    assert [(s.fetched, s.processed, s.created, s.refreshed, s.usable_odds) for s in service.source_imports] == [
        (1, 1, 1, 0, 1), (1, 1, 1, 0, 1),
    ]
    second = service.import_games("NBA")
    assert [g.id for g in second] == original_ids
    assert db.query(Game).count() == 2
    assert db.query(Odds).count() == 2
    assert [(s.created, s.refreshed) for s in service.source_imports] == [(0, 1), (0, 1)]
    assert all(s.game_date_min == s.game_date_max for s in service.source_imports)
    for odds in db.query(Odds).all():
        assert (odds.spread_home, odds.spread_away, odds.moneyline_home, odds.moneyline_away, odds.total) == (
            -7.5, 7.5, -280, 230, 212.5,
        )


def test_regular_source_cannot_overwrite_preseason_marker(db, caplog):
    row = event("same-provider-id")
    service = importer(db, {KEYS[1]: [row]})
    game = service.import_games("NBA")[0]
    service.live_data.fetch_games.side_effect = lambda key: [row] if key == KEYS[0] else []
    assert service.import_games("NBA") == []
    db.refresh(game)
    assert game.league == NBA_PRESEASON
    assert db.query(Game).count() == 1
    assert service.source_imports[0].errors == 1
    assert "provider_source=basketball_nba" in caplog.text


@pytest.mark.parametrize("failed_key", KEYS)
@pytest.mark.parametrize("failure", [
    RuntimeError("apiKey=secret-must-not-log"), None,
    requests.HTTPError("404 https://provider.invalid?apiKey=secret-must-not-log"),
])
def test_odds_source_failure_does_not_suppress_other_source(db, caplog, failed_key, failure):
    service = importer(db, {})
    def fetch(key):
        if key == failed_key:
            if failure is not None:
                raise failure
            return {"message": "source unavailable"}
        return [event(key)]
    service.live_data.fetch_games.side_effect = fetch
    games = service.import_games("NBA")
    assert len(games) == 1
    assert games[0].sport == "NBA"
    assert games[0].league == ("NBA" if failed_key == KEYS[1] else NBA_PRESEASON)
    assert sum(s.errors for s in service.source_imports) == 1
    assert "secret-must-not-log" not in caplog.text


@pytest.mark.parametrize("league_key", [*KEYS, "NCAAF"])
def test_reused_identical_snapshot_honors_current_profile(db, league_key):
    sport = "NBA" if league_key in KEYS else league_key
    rows = {league_key: [event("nba-event")]}
    service = importer(db, rows)
    game = service.import_games(sport)[0]
    engine = prediction_engine()
    engine.simulation_engine.simulate = MagicMock(return_value={
        "win_probability": 62, "runs": 10000, "average_margin": 4,
    })
    profiles = NPIWeightProfileService()
    profiles.create_profile(db, sport, "NPI-4.0", engine.npi_engine.DEFAULT_WEIGHTS)
    first = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    assert [p.market for p in first] == ["spread", "moneyline", "total"]
    assert {p.model_version for p in first} == {"NPI-5.0"}
    first_ids = [p.id for p in first]
    first_snapshots = [p.odds_snapshot_id for p in first]
    assert [p.id for p in engine.analyze_markets(db=db, game_id=game.id, persist=True)] == first_ids
    profiles.create_profile(db, sport, "NPI-4.0", {
        "home_advantage": 10, "spread_value": 20, "market_environment": 10,
        "situational_edge": 10, "historical_rules": 150,
    })
    service.import_games(sport)
    repeated = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    assert [p.id for p in repeated] != first_ids
    assert [p.odds_snapshot_id for p in repeated] == first_snapshots
    assert first[0].npi_score == 97.25
    assert repeated[0].npi_score == 69.5
    latest = db.query(Odds).order_by(Odds.id.desc()).first()
    assert all(p.odds_snapshot_id == latest.id and p.odds_observed_at == latest.created_at for p in repeated)
    assert db.query(Prediction).count() == 6
    assert db.query(Odds).count() == 1
    for outcome in rows[league_key][0]["bookmakers"][0]["markets"][2]["outcomes"]:
        outcome["point"] = 220.5
    service.import_games(sport)
    changed = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    assert [p.id for p in changed] != first_ids
    assert next(p.line_value for p in changed if p.market == "total") == 220.5
    assert len({p.odds_snapshot_id for p in changed}) == 1
    assert changed[0].odds_snapshot_id == db.query(Odds).order_by(Odds.id.desc()).first().id


def test_worker_reports_each_source_and_keeps_prediction_summary(db, monkeypatch, caplog):
    caplog.set_level("INFO")
    service = importer(db, {
        KEYS[0]: [event("without-odds", with_odds=False)],
        KEYS[1]: [event("preseason")],
    })
    monkeypatch.setenv("UPCOMING_GAME_SPORTS", "NBA")
    monkeypatch.setattr(upcoming_game_worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(upcoming_game_worker, "GameOddsImporter", lambda **_kwargs: service)
    monkeypatch.setattr(upcoming_game_worker, "PredictionEngine", prediction_engine)
    result = upcoming_game_worker.run_once()["NBA"]
    assert result["imported"] == 2
    assert result["predictions_generated"] == 3
    assert result["predictions_skipped_no_odds"] == 1
    assert service.source_imports[0].skipped_no_odds == 1
    assert service.source_imports[1].predictions == 3
    source_logs = [r.message for r in caplog.records if "Upcoming competition sync" in r.message]
    assert len(source_logs) == 2
    for message in source_logs:
        for key in ("provider_source=", "fetched=", "processed=", "created=", "refreshed=",
                    "usable_odds=", "skipped_no_odds=", "predictions=", "errors=",
                    "game_date_min=", "game_date_max="):
            assert key in message


def test_preseason_finals_settle_exact_ids_and_preserve_phase(db, caplog):
    rows = {KEYS[0]: [event("regular")], KEYS[1]: [event("preseason")]}
    games = importer(db, rows).import_games("NBA")
    engine = prediction_engine()
    for game in games:
        engine.analyze_markets(db=db, game_id=game.id, persist=True)
    client = MagicMock()
    client.get_scores.side_effect = lambda key, **_kwargs: [
        final(rows[key][0]),
        final(event("unmatched-exact-id")),
    ]
    service = FinalScoreSettlementService(provider_client=client)
    first = service.sync_sport(db, "NBA")
    assert [call.args[0] for call in client.get_scores.call_args_list] == list(KEYS)
    assert first.finalized == 2
    assert first.unmatched == 2
    assert first.settled == 2
    assert first.errors == 0
    assert db.query(PredictionResult).count() == 6
    assert {g.provider_game_id: g.league for g in db.query(Game).all()} == {
        "regular": "NBA", "preseason": NBA_PRESEASON,
    }
    assert "unmatched-exact-id" in caplog.text
    second = service.sync_sport(db, "NBA")
    assert second.already_final == 2
    assert second.settled == 0
    assert db.query(PredictionResult).count() == 6
    assert db.query(Game).count() == 2


@pytest.mark.parametrize("failed_key", KEYS)
@pytest.mark.parametrize("failure", [
    RuntimeError("apiKey=secret-must-not-log"),
    requests.HTTPError("404 https://provider.invalid?apiKey=secret-must-not-log"),
])
def test_score_source_failure_does_not_suppress_other_source(db, caplog, failed_key, failure):
    rows = {key: [event(key)] for key in KEYS}
    importer(db, rows).import_games("NBA")
    client = MagicMock()
    def scores(key, **_kwargs):
        if key == failed_key:
            raise failure
        return [final(rows[key][0])]
    client.get_scores.side_effect = scores
    result = FinalScoreSettlementService(provider_client=client).sync_sport(db, "NBA")
    assert result.finalized == 1
    assert result.errors == 1
    assert "secret-must-not-log" not in caplog.text
    assert [call.args[0] for call in client.get_scores.call_args_list] == list(KEYS)


@pytest.mark.parametrize("sport", ["NFL", "NCAAF", "NCAAB", "WNBA"])
def test_single_score_source_failure_propagates_without_credentials(db, sport, caplog):
    client = MagicMock()
    client.get_scores.side_effect = requests.HTTPError(
        "404 https://provider.invalid?apiKey=secret-must-not-log",
    )
    with pytest.raises(requests.HTTPError):
        FinalScoreSettlementService(provider_client=client).sync_sport(db, sport)
    assert client.get_scores.call_count == 1
    assert "secret-must-not-log" not in caplog.text


def test_invalid_json_error_is_sanitized_without_losing_failure_type():
    from app.services.odds_provider_client import safe_sync_error
    error = requests.exceptions.JSONDecodeError("apiKey=secret-must-not-log", "", 0)
    sanitized = safe_sync_error(error, KEYS[0])
    assert isinstance(sanitized, requests.exceptions.JSONDecodeError)
    assert "secret-must-not-log" not in str(sanitized)


def add_results(db, league):
    key = KEYS[1] if league == NBA_PRESEASON else KEYS[0]
    game = importer(db, {key: [event(league)]}).import_games("NBA")[0]
    game.game_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    game.status = "final"
    for version in ("NPI-4.0", "NPI-5.0", "unknown-history"):
        for market, selection in (("spread", "HOME"), ("moneyline", "AWAY"), ("total", "OVER")):
            prediction = Prediction(
                game_id=game.id, market=market, selection=selection,
                model_version=version, line_value=-3.5, american_odds=-110,
                npi_score=110, confidence_score=80, simulation_probability=62, projected_edge=5,
            )
            db.add(prediction)
            db.flush()
            db.add(PredictionResult(
                prediction_id=prediction.id, outcome="WIN", actual_result="115-100",
                predicted_result=selection, profit_loss=100,
            ))
    db.commit()


@pytest.mark.parametrize("days", [7, 30, 90])
def test_all_performance_sections_exclude_preseason_without_deleting_history(db, days):
    add_results(db, "NBA")
    service = V1ReadService()
    baseline = service.get_performance(db)
    intelligence = service.get_performance_intelligence(db, days=days)
    intelligence.pop("generated_at")
    analytics = PerformanceEngine().calculate_metrics(db)
    assert baseline["total_predictions"] == 3
    assert analytics["total_predictions"] == 3
    add_results(db, NBA_PRESEASON)
    preseason_prediction = (
        db.query(Prediction).join(Game, Game.id == Prediction.game_id)
        .filter(Game.league == NBA_PRESEASON).first()
    )
    db.add(UserPrediction(user_id=101, prediction_id=preseason_prediction.id))
    db.commit()
    actual = service.get_performance_intelligence(db, days=days)
    actual.pop("generated_at")
    assert actual == intelligence
    assert service.get_performance(db) == baseline
    assert PerformanceEngine().calculate_metrics(db) == analytics
    assert db.query(Prediction).count() == 18
    assert db.query(PredictionResult).count() == 18
    assert db.query(UserPrediction).count() == 1
    assert service.get_saved_picks(db=db, user_id=101)["count"] == 1


def test_upcoming_and_daily_card_include_future_preseason_not_started_games(db):
    future = event("future-preseason")
    started = event("started-preseason", start=datetime.now(timezone.utc) - timedelta(hours=1))
    games = importer(db, {KEYS[1]: [future, started]}).import_games("NBA")
    engine = prediction_engine()
    # Generate before changing kickoff to the past, preserving existing eligibility rules.
    past = games[1].game_date
    games[1].game_date = games[0].game_date
    db.commit()
    for game in games:
        engine.analyze_markets(db=db, game_id=game.id, persist=True)
    games[1].game_date = past
    db.commit()
    service = V1ReadService()
    upcoming = service.get_upcoming_predictions(db=db, sport="NBA")
    daily = service.get_daily_card(db=db, sport="NBA")
    assert upcoming["count"] > 0
    assert daily["count"] > 0
    assert {p["game_id"] for p in upcoming["predictions"]} == {games[0].id}
    picks = [daily["best_bet"], *daily["featured_picks"], *daily["next_best"]]
    assert {p["prediction"]["game_id"] for p in picks if p is not None} == {games[0].id}


def test_start_time_offsets_are_normalized_to_utc(db):
    row = event("offset")
    row["commence_time"] = "2026-10-05T23:30:00-04:00"
    game = importer(db, {KEYS[1]: [row]}).import_games("NBA")[0]
    assert game.game_date == datetime(2026, 10, 6, 3, 30)
    assert game.season == 2026


def test_legacy_analytics_history_and_calibration_also_exclude_preseason(db):
    games = importer(db, {KEYS[0]: [event("regular")], KEYS[1]: [event("preseason")]}).import_games("NBA")
    for game in games:
        prediction = NikScore(game_id=game.id, model_version="legacy-test")
        db.add(prediction)
        db.flush()
        db.add(PredictionOutcome(
            prediction_id=prediction.id, game_id=game.id, predicted_winner="HOME",
            actual_winner="HOME", predicted_confidence=80, prediction_correct=True,
        ))
    db.commit()
    assert len(analytics_repository.get_evaluations(db)) == 1
    assert len(analytics_repository.get_sport_accuracy_rows(db)) == 1
    assert len(analytics_repository.get_model_accuracy_rows(db)) == 1
    assert len(analytics_repository.get_evaluation_trend_rows(db)) == 1
    assert CalibrationService().calculate_calibration(db=db)["total_predictions"] == 1
    assert PredictionOutcomeService().update_prediction_metrics(db)["total_outcomes"] == 1
    assert ConfidenceService().get_average_confidence(db) == 80
    assert db.query(PredictionOutcome).count() == 2


def test_bad_event_does_not_suppress_later_events_or_score_rows(db):
    service = importer(db, {KEYS[0]: [{"id": "malformed"}], KEYS[1]: [event("valid")]})
    game = service.import_games("NBA")[0]
    assert game.provider_game_id == "valid"
    assert service.source_imports[0].errors == 1
    client = MagicMock()
    client.get_scores.side_effect = lambda key, **_kwargs: (
        [None] if key == KEYS[0] else [None, final(event("valid"))]
    )
    summary = FinalScoreSettlementService(provider_client=client).sync_sport(db, "NBA")
    assert summary.errors == 2
    assert summary.finalized == 1


@pytest.mark.parametrize("sport", ["NFL", "NCAAF", "NCAAB", "WNBA"])
@pytest.mark.parametrize("event_failure", [False, True])
def test_single_source_failures_propagate_and_scheduler_marks_failed(db, sport, event_failure, caplog):
    service = importer(db, {})
    if event_failure:
        service.live_data.fetch_games.return_value = [{"id": "bad"}]
        service.live_data.fetch_games.side_effect = None
        exception = KeyError
    else:
        service.live_data.fetch_games.side_effect = requests.HTTPError(
            "404 https://provider.invalid?apiKey=secret-must-not-log",
        )
        exception = requests.HTTPError
    with pytest.raises(exception):
        service.import_games(sport)
    scheduler = JobScheduler(prediction_engine=MagicMock())
    stages = []
    scheduler._run_stage("import_games", sport, stages, lambda: service.import_games(sport), [])
    assert stages[0]["status"] == "failed"
    assert "secret-must-not-log" not in caplog.text


def test_all_nba_sources_failing_is_not_successful_empty_import(db, caplog):
    service = importer(db, {})
    service.live_data.fetch_games.side_effect = requests.HTTPError(
        "404 https://provider.invalid?apiKey=secret-must-not-log",
    )
    with pytest.raises(RuntimeError, match="All NBA competition sources failed"):
        service.import_games("NBA")
    assert service.live_data.fetch_games.call_count == 2
    scheduler = JobScheduler(prediction_engine=MagicMock())
    stages = []
    scheduler._run_stage("import_games", "NBA", stages, lambda: service.import_games("NBA"), [])
    assert stages[0]["status"] == "failed"
    assert "secret-must-not-log" not in caplog.text


def test_all_sources_failure_is_visible_in_worker_summary(db, caplog, monkeypatch):
    import app.workers.upcoming_game_worker as worker
    service = importer(db, {})
    service.live_data.fetch_games.side_effect = requests.HTTPError(
        "404 https://provider.invalid?apiKey=secret-must-not-log",
    )
    monkeypatch.setattr(worker, "_configured_sports", lambda: ("NBA",))
    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    monkeypatch.setattr(worker, "GameOddsImporter", lambda **kwargs: service)
    caplog.set_level("INFO")
    result = worker.run_once()
    assert result["NBA"]["imported"] == 0
    assert "sport=NBA imported=0 import_errors=1" in caplog.text
    assert service.live_data.fetch_games.call_count == 2
    assert "All NBA competition sources failed" in caplog.text
    assert all(f"provider_source={key}" in caplog.text for key in KEYS)
    assert "secret-must-not-log" not in caplog.text
