from app.services.snapshot_replay_service import (
    SnapshotReplayService
)


def test_get_snapshots_delegates_to_backtest_service():

    expected = ["snapshot-a", "snapshot-b"]

    class _FakeBacktestService:
        def __init__(self):
            self.calls = []

        def get_snapshots(self, db, limit):
            self.calls.append((db, limit))
            return expected

    fake_backtest = _FakeBacktestService()
    service = SnapshotReplayService(backtest_service=fake_backtest)
    db = object()

    result = service.get_snapshots(db, 25)

    assert fake_backtest.calls == [(db, 25)]
    assert result == expected


def test_replay_delegates_to_backtest_service():

    expected = ["eval-1"]

    class _FakeBacktestService:
        def __init__(self):
            self.calls = []

        def replay(self, db, snapshots):
            self.calls.append((db, snapshots))
            return expected

    fake_backtest = _FakeBacktestService()
    service = SnapshotReplayService(backtest_service=fake_backtest)
    db = object()
    snapshots = ["s1"]

    result = service.replay(db, snapshots)

    assert fake_backtest.calls == [(db, snapshots)]
    assert result == expected
