from sqlalchemy.orm import Session

from app.services.prediction_service import PredictionService
from app.services.prediction_snapshot_service import (
    PredictionSnapshotService,
)
from app.services.model_version_service import (
    ModelVersionService,
)


class PredictionLifecycleService:
    """
    Coordinates the end-to-end prediction workflow.
    """

    def __init__(
        self,
        prediction_service=None,
        snapshot_service=None,
        version_service=None,
    ):
        self.prediction_service = (
            prediction_service or PredictionService()
        )
        self.snapshot_service = (
            snapshot_service or PredictionSnapshotService()
        )
        self.version_service = (
            version_service or ModelVersionService()
        )

    def process_game(
        self,
        db: Session,
        game_id: int,
    ):
        """
        Generate and persist a prediction.

        Snapshot creation should already happen inside
        PredictionService if Sprint 7.2 integration is complete.
        """

        prediction = self.prediction_service.generate_prediction(
            db,
            game_id,
        )

        return prediction
