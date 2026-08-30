from unittest.mock import MagicMock, patch

from app.workers import final_score_worker


def test_configured_sports_defaults(monkeypatch):
    monkeypatch.delenv("FINAL_SCORE_SPORTS", raising=False)

    assert final_score_worker._configured_sports() == (
        "NFL",
        "NBA",
        "NCAAF",
        "NCAAB",
        "WNBA",
    )


def test_configured_sports_can_be_overridden(monkeypatch):
    monkeypatch.setenv(
        "FINAL_SCORE_SPORTS",
        "NCAAF,NFL",
    )

    assert final_score_worker._configured_sports() == (
        "NCAAF",
        "NFL",
    )


def test_poll_seconds_has_safe_minimum(monkeypatch):
    monkeypatch.setenv(
        "FINAL_SCORE_POLL_SECONDS",
        "10",
    )

    assert final_score_worker._poll_seconds() == 60


def test_run_once_syncs_each_configured_sport(monkeypatch):
    monkeypatch.setenv(
        "FINAL_SCORE_SPORTS",
        "NCAAF,NFL",
    )

    fake_db = MagicMock()
    fake_session_local = MagicMock(
        side_effect=[fake_db, fake_db],
    )

    summary_ncaaf = MagicMock(
        sport="NCAAF",
        fetched=10,
        matched=2,
        updated=2,
        settled=2,
        skipped=8,
        errors=0,
    )

    summary_nfl = MagicMock(
        sport="NFL",
        fetched=5,
        matched=1,
        updated=1,
        settled=1,
        skipped=4,
        errors=0,
    )

    fake_service = MagicMock()
    fake_service.sync_sport.side_effect = [
        summary_ncaaf,
        summary_nfl,
    ]

    with (
        patch.object(
            final_score_worker,
            "SessionLocal",
            fake_session_local,
        ),
        patch.object(
            final_score_worker,
            "OddsProviderClient",
            return_value=MagicMock(),
        ),
        patch.object(
            final_score_worker,
            "FinalScoreSettlementService",
            return_value=fake_service,
        ),
    ):
        results = final_score_worker.run_once()

    assert fake_service.sync_sport.call_count == 2

    assert results["NCAAF"]["settled"] == 2
    assert results["NFL"]["settled"] == 1

    assert fake_db.close.call_count == 2