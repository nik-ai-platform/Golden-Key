class LeaderboardService:
    def build_leaderboard(self, entries: list[dict], category: str = "overall") -> list[dict]:
        ranked = sorted(entries, key=lambda item: float(item.get("score", 0)), reverse=True)
        return [{"category": category, **entry} for entry in ranked]
