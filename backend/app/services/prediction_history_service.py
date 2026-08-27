from sqlalchemy.orm import Session

from app.models.prediction_history import PredictionHistory


class PredictionHistoryService:
    def record_prediction(self, db: Session, payload: dict):
        record = PredictionHistory(
            game_id=payload.get("game_id"),
            model_version=payload.get("model_version"),
            prediction=payload.get("prediction"),
            confidence=payload.get("confidence"),
            spread_prediction=payload.get("spread_prediction"),
            market_line=payload.get("market_line"),
            recommended_bet=payload.get("recommended_bet"),
            result_status=payload.get("result_status"),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def list_history(self, db: Session, limit: int = 10):
        return db.query(PredictionHistory).order_by(PredictionHistory.id.desc()).limit(limit).all()

    def export_history(self, db: Session):
        rows = self.list_history(db, limit=1000)
        return [
            {
                "id": row.id,
                "game_id": row.game_id,
                "model_version": row.model_version,
                "prediction": row.prediction,
                "confidence": row.confidence,
                "spread_prediction": row.spread_prediction,
                "market_line": row.market_line,
                "recommended_bet": row.recommended_bet,
                "result_status": row.result_status,
            }
            for row in rows
        ]

    def clear_history(self, db: Session):
        deleted_count = db.query(PredictionHistory).delete()
        db.commit()
        return {"deleted_count": deleted_count}
