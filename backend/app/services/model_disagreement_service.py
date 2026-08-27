class ModelDisagreementService:

    def assess(self, predictions):
        if not predictions:
            return {"disagreement_level": "LOW_DISAGREEMENT", "recommendation": "Proceed"}

        predictions_set = {item.get("prediction") for item in predictions}
        if len(predictions_set) >= 2:
            return {"disagreement_level": "HIGH_DISAGREEMENT", "recommendation": "Reduce confidence"}
        return {"disagreement_level": "LOW_DISAGREEMENT", "recommendation": "Proceed"}
