from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.models.prediction_line_correction import PredictionLineCorrection
from app.models.prediction_record import Prediction
from app.services.result_settlement_service import ResultSettlementService


class PredictionLineCorrectionService:
    def __init__(
        self,
        settlement_service: ResultSettlementService | None = None,
    ) -> None:
        self.settlement_service = settlement_service or ResultSettlementService()

    def correct_and_regrade(
        self,
        db: Session,
        *,
        prediction_id: int,
        corrected_line: float,
        reason: str,
        source: str | None = None,
    ) -> tuple[PredictionLineCorrection, object]:
        prediction = db.get(Prediction, prediction_id)
        if prediction is None:
            raise ValueError(f"Prediction {prediction_id} not found")
        if prediction.market.lower() not in {"spread", "ats", "total", "totals", "over_under"}:
            raise ValueError(f"Prediction {prediction_id} does not use a line")
        if not reason.strip():
            raise ValueError("Correction reason is required")
        if not math.isfinite(corrected_line):
            raise ValueError("Corrected line must be finite")

        correction = PredictionLineCorrection(
            prediction_id=prediction.id,
            original_line=prediction.line_value,
            corrected_line=corrected_line,
            reason=reason.strip(),
            source=source.strip() if source and source.strip() else None,
        )
        db.add(correction)
        prediction.line_value = corrected_line

        try:
            result = self.settlement_service.regrade_prediction(
                db=db,
                prediction_id=prediction.id,
            )
        except Exception:
            db.rollback()
            raise

        db.refresh(correction)
        return correction, result