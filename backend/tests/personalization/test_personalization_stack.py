from app.services.user_intelligence_service import UserIntelligenceService
from app.services.personalized_prediction_service import PersonalizedPredictionService
from app.services.dashboard_personalization_service import DashboardPersonalizationService
from app.services.daily_briefing_service import DailyBriefingService
from app.services.risk_intelligence_service import RiskIntelligenceService
from app.services.user_feedback_learning_service import UserFeedbackLearningService


def test_profile_creation():
    service = UserIntelligenceService()
    profile = service.build_profile(123)
    assert profile["user_id"] == 123
    assert profile["risk_level"] == "moderate"


def test_preference_updates():
    service = UserIntelligenceService()
    updated = service.update_preferences({"user_id": 123, "games_viewed": 20, "predictions_viewed": 40, "bets_accepted": 6, "bets_ignored": 3})
    assert updated["updated"] is True


def test_recommendation_matching():
    service = PersonalizedPredictionService()
    result = service.personalize({"title": "Miami +3", "confidence": 78}, 123)
    assert result["recommended_action"] in {"MATCH", "LOWER FIT"}


def test_risk_calculations():
    service = RiskIntelligenceService()
    result = service.analyze(bankroll=5000, bet_size=1000, exposure=0.42, variance=0.28, loss_streaks=4, market_risk=0.45)
    assert result["warning"] is True


def test_dashboard_customization():
    service = DashboardPersonalizationService()
    dashboard = service.build_dashboard({"preferred_sports": ["NFL"]})
    assert dashboard["preferred_metrics"]


def test_briefing_generation():
    service = DailyBriefingService()
    briefing = service.generate_briefing({"user_name": "Nik", "preferred_sports": ["NBA"]})
    assert briefing["headline"]


def test_feedback_learning():
    service = UserFeedbackLearningService()
    result = service.learn({"liked_prediction": True, "ignored_prediction": False, "followed_recommendation": True, "outcome": "win", "reason": "value"})
    assert result["updated_strategy"]
