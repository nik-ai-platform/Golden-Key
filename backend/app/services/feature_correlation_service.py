class FeatureCorrelationService:

    def assess_correlation(self, existing_feature, new_feature):
        if not existing_feature or not new_feature:
            return {"correlation_level": "Low Correlation", "recommendation": "APPROVE"}

        existing_name = str(existing_feature.get("feature_name", "")).lower()
        new_name = str(new_feature.get("feature_name", "")).lower()

        if existing_name == new_name:
            return {"correlation_level": "High Correlation", "recommendation": "REVIEW"}
        if "rating" in existing_name and "rating" in new_name:
            return {"correlation_level": "High Correlation", "recommendation": "REVIEW"}
        return {"correlation_level": "Low Correlation", "recommendation": "APPROVE"}
