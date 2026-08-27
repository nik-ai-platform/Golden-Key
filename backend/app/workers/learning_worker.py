from __future__ import annotations

from app.services.cross_sport_learning_service import CrossSportLearningService


def run_learning_worker() -> dict:
    service = CrossSportLearningService()
    return {
        "status": "completed",
        "learning": service.transfer_patterns(),
    }
