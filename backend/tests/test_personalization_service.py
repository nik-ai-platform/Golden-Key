from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.services.personalization_service import PersonalizationService
from app.services.user_risk_service import UserRiskService


def test_profiles_save_correctly():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        service = PersonalizationService()
        profile = service.save_user_profile(
            db,
            {
                "user_id": 101,
                "risk_level": "MODERATE",
                "preferred_sports": ["NFL", "NBA"],
                "preferred_markets": ["ATS", "Moneyline"],
                "betting_style": "balanced",
            },
        )
        assert profile.user_id == 101
        assert profile.risk_level == "MODERATE"
    finally:
        db.close()


def test_preferences_filter_recommendations():
    service = PersonalizationService()
    bets = [
        {"id": "a", "confidence": 85, "edge": 4.1, "parlay": False, "volatility": "low"},
        {"id": "b", "confidence": 72, "edge": 2.5, "parlay": True, "volatility": "high"},
    ]
    preferences = {"minimum_confidence": 75, "minimum_edge": 3, "max_parlay_legs": 2, "avoid_high_variance": True}

    filtered = service.filter_recommendations(bets, preferences)

    assert len(filtered) == 1
    assert filtered[0]["id"] == "a"


def test_risk_levels_work():
    service = UserRiskService()
    filters = service.get_risk_filters("CONSERVATIVE")

    assert filters["minimum_confidence"] == 80
    assert filters["allow_parlays"] is False


def test_personalization_does_not_alter_predictions():
    service = PersonalizationService()
    predictions = [{"id": 1, "confidence": 84, "winner": "DAL"}]
    profile = {"risk_level": "CONSERVATIVE"}

    personalized = service.personalize_predictions(predictions, profile)

    assert personalized[0]["confidence"] == 84
    assert personalized[0]["winner"] == "DAL"
    assert personalized[0]["personalized_score"] > 0


def test_feedback_stores_correctly():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        service = PersonalizationService()
        feedback = service.save_feedback(
            db,
            {
                "user_id": 202,
                "prediction_helpful": True,
                "recommendation_used": True,
                "confidence_accuracy": 0.81,
                "user_rating": 5,
                "comments": "Great pick",
            },
        )
        assert feedback.user_id == 202
        assert feedback.prediction_helpful is True
    finally:
        db.close()


def test_missing_preferences_handled_safely():
    service = PersonalizationService()
    bets = [{"id": "x", "confidence": 70, "edge": 1.8, "parlay": False, "volatility": "low"}]

    filtered = service.filter_recommendations(bets, None)

    assert len(filtered) == 1
