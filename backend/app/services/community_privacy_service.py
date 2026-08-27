class CommunityPrivacyService:
    def build_preferences(self, payload: dict) -> dict:
        return {
            "public_profile": payload.get("public_profile", True),
            "private_bets": payload.get("private_bets", False),
            "followers_only": payload.get("followers_only", False),
            "anonymous_sharing": payload.get("anonymous_sharing", False),
            "hide_bankroll": payload.get("hide_bankroll", False),
        }
