from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.services.prediction_history_service import PredictionHistoryService


def test_prediction_history_can_be_cleared_and_exported():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        service = PredictionHistoryService()
        service.record_prediction(
            db,
            {
                "game_id": 7,
                "model_version": "v1",
                "prediction": "PHI",
                "confidence": 77,
                "spread_prediction": "+3",
                "market_line": "+2.5",
                "recommended_bet": "PHI +2.5",
                "result_status": "PENDING",
            },
        )

        export_payload = service.export_history(db)
        assert len(export_payload) == 1
        assert export_payload[0]["prediction"] == "PHI"

        cleared = service.clear_history(db)
        assert cleared["deleted_count"] == 1
        assert service.list_history(db, limit=10) == []
    finally:
        db.close()
