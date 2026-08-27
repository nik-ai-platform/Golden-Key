from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.services.prediction_history_service import PredictionHistoryService


def test_prediction_history_persists_to_database():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        service = PredictionHistoryService()
        record = service.record_prediction(
            db,
            {
                "game_id": 42,
                "model_version": "v2",
                "prediction": "DAL",
                "confidence": 81,
                "spread_prediction": "-3",
                "market_line": "-2.5",
                "recommended_bet": "DAL -2.5",
                "result_status": "PENDING",
            },
        )

        rows = service.list_history(db, limit=5)
        assert record.id is not None
        assert len(rows) == 1
        assert rows[0].prediction == "DAL"
    finally:
        db.close()
