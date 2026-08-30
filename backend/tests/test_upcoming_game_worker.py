from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from app.services.odds_service import NoCompleteOddsSnapshotError
from app.workers import upcoming_game_worker


def test_configured_sports_defaults(monkeypatch):
    monkeypatch.delenv("UPCOMING_GAME_SPORTS", raising=False)

    assert upcoming_game_worker._configured_sports() == (
        "NFL",
        "NBA",
        "NCAAF",
        "NCAAB",
        "WNBA",
    )


def test_configured_sports_parses_override(monkeypatch):
    monkeypatch.setenv(
        "UPCOMING_GAME_SPORTS",
        " ncaaf, NFL ,, wnba ",
    )

    assert upcoming_game_worker._configured_sports() == (
        "NCAAF",
        "NFL",
        "WNBA",
    )


def test_poll_seconds_has_safe_minimum(monkeypatch):
    monkeypatch.setenv("UPCOMING_GAME_POLL_SECONDS", "60")

    assert upcoming_game_worker._poll_seconds() == 300


def test_run_once_imports_and_predicts_with_session_per_sport(monkeypatch):
    monkeypatch.setenv("UPCOMING_GAME_SPORTS", "NCAAF,NFL")
    ncaaf_db = MagicMock()
    nfl_db = MagicMock()
    session_local = MagicMock(side_effect=[ncaaf_db, nfl_db])
    ncaaf_games = [SimpleNamespace(id=10), SimpleNamespace(id=11)]
    nfl_games = [SimpleNamespace(id=20)]
    ncaaf_importer = MagicMock()
    nfl_importer = MagicMock()
    ncaaf_importer.import_games.return_value = ncaaf_games
    nfl_importer.import_games.return_value = nfl_games
    importer_class = MagicMock(
        side_effect=[ncaaf_importer, nfl_importer],
    )
    engine = MagicMock()
    engine.analyze_markets.side_effect = [
        [MagicMock(), MagicMock(), MagicMock()],
        [MagicMock(), MagicMock(), MagicMock()],
        [MagicMock(), MagicMock(), MagicMock()],
    ]

    with (
        patch.object(
            upcoming_game_worker,
            "SessionLocal",
            session_local,
        ),
        patch.object(
            upcoming_game_worker,
            "GameOddsImporter",
            importer_class,
        ),
        patch.object(
            upcoming_game_worker,
            "PredictionEngine",
            return_value=engine,
        ),
    ):
        results = upcoming_game_worker.run_once()

    assert session_local.call_count == 2
    assert importer_class.call_args_list == [
        call(db=ncaaf_db),
        call(db=nfl_db),
    ]
    ncaaf_importer.import_games.assert_called_once_with("NCAAF")
    nfl_importer.import_games.assert_called_once_with("NFL")
    assert engine.analyze_markets.call_args_list == [
        call(db=ncaaf_db, game_id=10, persist=True),
        call(db=ncaaf_db, game_id=11, persist=True),
        call(db=nfl_db, game_id=20, persist=True),
    ]
    assert results == {
        "NCAAF": {
            "sport": "NCAAF",
            "imported": 2,
            "predictions_generated": 6,
            "predictions_skipped_no_odds": 0,
            "prediction_errors": 0,
        },
        "NFL": {
            "sport": "NFL",
            "imported": 1,
            "predictions_generated": 3,
            "predictions_skipped_no_odds": 0,
            "prediction_errors": 0,
        },
    }
    ncaaf_db.close.assert_called_once_with()
    nfl_db.close.assert_called_once_with()


def test_prediction_failure_does_not_stop_next_game(monkeypatch):
    monkeypatch.setenv("UPCOMING_GAME_SPORTS", "NFL")
    db = MagicMock()
    importer = MagicMock()
    importer.import_games.return_value = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]
    engine = MagicMock()
    engine.analyze_markets.side_effect = [
        RuntimeError("prediction failed"),
        [MagicMock(), MagicMock(), MagicMock()],
    ]

    with (
        patch.object(
            upcoming_game_worker,
            "SessionLocal",
            return_value=db,
        ),
        patch.object(
            upcoming_game_worker,
            "GameOddsImporter",
            return_value=importer,
        ),
        patch.object(
            upcoming_game_worker,
            "PredictionEngine",
            return_value=engine,
        ),
    ):
        results = upcoming_game_worker.run_once()

    assert engine.analyze_markets.call_args_list == [
        call(db=db, game_id=1, persist=True),
        call(db=db, game_id=2, persist=True),
    ]
    db.rollback.assert_called_once_with()
    db.close.assert_called_once_with()
    assert results["NFL"] == {
        "sport": "NFL",
        "imported": 2,
        "predictions_generated": 3,
        "predictions_skipped_no_odds": 0,
        "prediction_errors": 1,
    }


@pytest.mark.parametrize(
    "unavailable_reason",
    ["no bookmakers", "incomplete bookmaker markets"],
)
def test_unusable_odds_are_skipped_without_stopping_later_games(
    monkeypatch,
    unavailable_reason,
):
    monkeypatch.setenv("UPCOMING_GAME_SPORTS", "NCAAF")
    db = MagicMock()
    importer = MagicMock()
    importer.import_games.return_value = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]
    engine = MagicMock()
    engine.analyze_markets.side_effect = [
        NoCompleteOddsSnapshotError(unavailable_reason),
        [MagicMock(), MagicMock(), MagicMock()],
    ]

    with (
        patch.object(
            upcoming_game_worker,
            "SessionLocal",
            return_value=db,
        ),
        patch.object(
            upcoming_game_worker,
            "GameOddsImporter",
            return_value=importer,
        ),
        patch.object(
            upcoming_game_worker,
            "PredictionEngine",
            return_value=engine,
        ),
    ):
        results = upcoming_game_worker.run_once()

    assert engine.analyze_markets.call_args_list == [
        call(db=db, game_id=1, persist=True),
        call(db=db, game_id=2, persist=True),
    ]
    db.rollback.assert_not_called()
    assert results["NCAAF"] == {
        "sport": "NCAAF",
        "imported": 2,
        "predictions_generated": 3,
        "predictions_skipped_no_odds": 1,
        "prediction_errors": 0,
    }


def test_sport_failure_does_not_stop_next_sport(monkeypatch):
    monkeypatch.setenv("UPCOMING_GAME_SPORTS", "NBA,WNBA")
    nba_db = MagicMock()
    wnba_db = MagicMock()
    nba_importer = MagicMock()
    wnba_importer = MagicMock()
    nba_importer.import_games.side_effect = RuntimeError("import failed")
    wnba_importer.import_games.return_value = [SimpleNamespace(id=7)]
    engine = MagicMock()
    engine.analyze_markets.return_value = [
        MagicMock(),
        MagicMock(),
        MagicMock(),
    ]

    with (
        patch.object(
            upcoming_game_worker,
            "SessionLocal",
            side_effect=[nba_db, wnba_db],
        ),
        patch.object(
            upcoming_game_worker,
            "GameOddsImporter",
            side_effect=[nba_importer, wnba_importer],
        ),
        patch.object(
            upcoming_game_worker,
            "PredictionEngine",
            return_value=engine,
        ),
    ):
        results = upcoming_game_worker.run_once()

    nba_importer.import_games.assert_called_once_with("NBA")
    wnba_importer.import_games.assert_called_once_with("WNBA")
    engine.analyze_markets.assert_called_once_with(
        db=wnba_db,
        game_id=7,
        persist=True,
    )
    nba_db.rollback.assert_called_once_with()
    nba_db.close.assert_called_once_with()
    wnba_db.close.assert_called_once_with()
    assert results["NBA"] == {
        "sport": "NBA",
        "imported": 0,
        "predictions_generated": 0,
        "predictions_skipped_no_odds": 0,
        "prediction_errors": 0,
    }
    assert results["WNBA"]["predictions_generated"] == 3


def test_run_forever_survives_cycle_failure(monkeypatch):
    monkeypatch.setenv("UPCOMING_GAME_POLL_SECONDS", "300")
    run_once = MagicMock(
        side_effect=[RuntimeError("cycle failed"), None],
    )
    sleep = MagicMock(side_effect=[None, KeyboardInterrupt])

    with (
        patch.object(upcoming_game_worker, "run_once", run_once),
        patch.object(upcoming_game_worker.time, "sleep", sleep),
        pytest.raises(KeyboardInterrupt),
    ):
        upcoming_game_worker.run_forever()

    assert run_once.call_count == 2
    assert sleep.call_args_list == [call(300), call(300)]