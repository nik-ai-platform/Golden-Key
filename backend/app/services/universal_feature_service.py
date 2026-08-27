class UniversalFeatureService:
    def track_feature(self, feature_name, sport, is_universal=True):
        return {
            "feature": feature_name,
            "sport": sport,
            "is_universal": is_universal,
            "usage": ["NBA", "NFL", "NCAAB"] if is_universal else [sport],
        }

    def list_features(self):
        return [
            self.track_feature("Rest Advantage", "NBA", True),
            self.track_feature("Pace Differential", "NBA", False),
        ]
