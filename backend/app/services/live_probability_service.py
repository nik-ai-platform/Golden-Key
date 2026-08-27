class LiveProbabilityService:
    def estimate_probabilities(self, win_probability=None, cover_probability=None, total_probability=None):
        return {
            "win_probability": round(float(win_probability or 0.55) * 100, 2),
            "cover_probability": round(float(cover_probability or 0.6) * 100, 2),
            "total_probability": round(float(total_probability or 0.5) * 100, 2),
        }
