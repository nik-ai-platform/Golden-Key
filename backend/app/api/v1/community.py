from fastapi import APIRouter, Depends

from app.auth.dependencies import require_viewer
from app.services.community_context_service import CommunityContextService
from app.services.community_intelligence_service import CommunityIntelligenceService
from app.services.community_privacy_service import CommunityPrivacyService
from app.services.expert_ranking_service import ExpertRankingService
from app.services.leaderboard_service import LeaderboardService
from app.services.reputation_service import ReputationService
from app.services.trust_service import TrustService

router = APIRouter(prefix="/community", tags=["Community"], dependencies=[Depends(require_viewer)])


@router.get("/profile")
def get_profile():
    return {"username": "SharpShooter23", "bio": "NBA value bettor", "verified": True}


@router.get("/feed")
def get_feed():
    return {"feed": ["Celtics -4.5", "Chiefs ML"], "consensus": 0.78}


@router.post("/follow")
def follow_user(payload: dict):
    return {"ok": True, "payload": payload}


@router.get("/leaderboard")
def get_leaderboard():
    service = LeaderboardService()
    return service.build_leaderboard([{"user_id": 1, "score": 94}, {"user_id": 2, "score": 88}], category="overall")


@router.get("/strategies")
def get_strategies():
    return [{"name": "NBA Underdog System", "sport": "NBA", "market": "ATS"}]


@router.get("/discussions")
def get_discussions():
    return [{"body": "Why is Golden Key fading this matchup?", "likes": 3}]


@router.get("/reputation")
def get_reputation():
    service = ReputationService()
    return service.calculate_reputation({"prediction_accuracy": 0.572, "roi": 0.18, "consistency": 0.82, "community_feedback": 0.9, "analysis_quality": 0.84, "longevity": 0.75, "verified": True})


@router.post("/context")
def get_context(payload: dict):
    service = CommunityContextService()
    return service.build_context(payload)


@router.get("/ranking")
def get_ranking():
    service = ExpertRankingService()
    return service.rank_users([{"user_id": 1, "performance": 0.58, "risk_adjusted_return": 0.16, "sample_size": 500, "consistency": 0.84, "transparency": 0.9}])


@router.get("/intelligence")
def get_intelligence():
    service = CommunityIntelligenceService()
    return service.analyze({"popular_picks": ["Chiefs ML"], "consensus": 0.78, "market_sentiment": "bullish", "emerging_trends": ["rest advantage"]})


@router.get("/trust")
def get_trust():
    service = TrustService()
    return service.evaluate({"fake_records": False, "cherry_picking": False, "deleted_losses": False, "suspicious_activity": False, "duplicate_accounts": False})


@router.get("/privacy")
def get_privacy():
    service = CommunityPrivacyService()
    return service.build_preferences({"public_profile": True})
