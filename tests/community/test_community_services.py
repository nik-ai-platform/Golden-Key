from app.services.reputation_service import ReputationService
from app.services.expert_ranking_service import ExpertRankingService
from app.services.community_intelligence_service import CommunityIntelligenceService
from app.services.leaderboard_service import LeaderboardService


def test_reputation_service_scores_profiles():
    service = ReputationService()
    result = service.calculate_reputation({"prediction_accuracy": 0.57, "roi": 0.18, "consistency": 0.82, "community_feedback": 0.9, "analysis_quality": 0.84, "longevity": 0.75, "verified": True})
    assert result["score"] >= 80


def test_expert_ranking_service_ranks_users():
    service = ExpertRankingService()
    ranked = service.rank_users([
        {"user_id": 1, "performance": 0.58, "risk_adjusted_return": 0.16, "sample_size": 500, "consistency": 0.84, "transparency": 0.9},
        {"user_id": 2, "performance": 0.6, "risk_adjusted_return": 0.14, "sample_size": 10, "consistency": 0.95, "transparency": 0.8},
    ])
    assert ranked[0]["user_id"] == 1


def test_community_intelligence_service_builds_consensus():
    service = CommunityIntelligenceService()
    result = service.analyze({"popular_picks": ["Chiefs ML", "Celtics -4.5"], "consensus": 0.78, "market_sentiment": "bullish", "emerging_trends": ["rest advantage"]})
    assert result["consensus_signal"] == "high"


def test_leaderboard_service_ranks_categories():
    service = LeaderboardService()
    result = service.build_leaderboard([{"user_id": 1, "score": 94}, {"user_id": 2, "score": 88}], category="overall")
    assert result[0]["user_id"] == 1
