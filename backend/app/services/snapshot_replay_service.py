from sqlalchemy.orm import Session

from app.services.analytics.backtest_service import (
    BacktestService
)


class SnapshotReplayService:
    """Compatibility wrapper for snapshot replay methods."""


    def __init__(
        self,
        backtest_service=None,
    ):
        self.backtest = (
            backtest_service or BacktestService()
        )


    def get_snapshots(
        self,
        db: Session,
        limit: int = 100
    ):
        return self.backtest.get_snapshots(db, limit)


    def evaluate_snapshot(
        self,
        db: Session,
        snapshot,
        actual_winner
    ):
        return self.backtest.evaluate_snapshot(
            db,
            snapshot,
            actual_winner
        )


    def replay(
        self,
        db: Session,
        snapshots
    ):
        return self.backtest.replay(
            db,
            snapshots
        )
