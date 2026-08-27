from app.services.community_intelligence_service import CommunityIntelligenceService


class CommunityContextService:
    def build_context(self, payload: dict) -> dict:
        intelligence = CommunityIntelligenceService().analyze(payload)
        return {
            "community_summary": intelligence,
            "response": f"{int(intelligence['consensus'] * 100)}% of verified users favor this matchup.",
        }
