class ExpertRankingService:
    def rank_users(self, users: list[dict]) -> list[dict]:
        ranked = []
        for user in users:
            performance = float(user.get("performance", 0.0))
            risk_adjusted_return = float(user.get("risk_adjusted_return", 0.0))
            sample_size = float(user.get("sample_size", 0.0))
            consistency = float(user.get("consistency", 0.0))
            transparency = float(user.get("transparency", 0.0))

            score = (
                (performance * 0.35)
                + (risk_adjusted_return * 0.25)
                + min(sample_size / 500.0, 1.0) * 0.15
                + (consistency * 0.15)
                + (transparency * 0.10)
            )
            ranked.append({**user, "ranking_score": round(score, 4)})

        return sorted(ranked, key=lambda item: item["ranking_score"], reverse=True)
