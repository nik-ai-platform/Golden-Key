class CrossSportAnalysisService:
    def analyze(self, feature_name, sport, predictive_strength, correlation, roi_impact):
        return {
            "feature": feature_name,
            "sport": sport,
            "predictive_strength": predictive_strength,
            "correlation": correlation,
            "roi_impact": roi_impact,
            "recommendation": "Prioritize NBA usage" if sport == "NBA" else "Evaluate cautiously",
        }
