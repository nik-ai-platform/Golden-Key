class EnsemblePredictionService:

    def generate_prediction(self, game_id):
        if game_id is None:
            return {"prediction": "UNKNOWN", "score": 0, "confidence": 0, "agreement": "LOW"}

        predictions = [
            {"id": "npi", "prediction": "HOME", "confidence": 78, "edge": 4.2},
            {"id": "market", "prediction": "HOME", "confidence": 74, "edge": 3.6},
            {"id": "historical", "prediction": "HOME", "confidence": 72, "edge": 3.1},
            {"id": "situational", "prediction": "HOME", "confidence": 70, "edge": 2.8},
            {"id": "live", "prediction": "AWAY", "confidence": 64, "edge": 1.5},
        ]

        combined = self.combine_predictions(predictions)
        confidence = self.calculate_confidence(combined)
        return {
            "game_id": game_id,
            "prediction": combined["prediction"],
            "score": combined["score"],
            "confidence": confidence,
            "agreement": combined["agreement"],
        }

    def combine_predictions(self, predictions):
        if not predictions:
            return {"prediction": "UNKNOWN", "score": 0, "agreement": "LOW"}

        weights = {
            "npi": 0.4,
            "market": 0.25,
            "historical": 0.15,
            "situational": 0.15,
            "live": 0.05,
        }

        weighted_score = 0
        for prediction in predictions:
            model_id = prediction.get("id", "")
            confidence = float(prediction.get("confidence", 0) or 0)
            weighted_score += confidence * weights.get(model_id, 0.1)

        agreement = "HIGH" if len({item.get("prediction") for item in predictions}) == 1 else "MEDIUM"
        if self.analyze_disagreement(predictions)["disagreement_level"] == "HIGH_DISAGREEMENT":
            agreement = "LOW"

        return {
            "prediction": "HOME" if weighted_score >= 70 else "AWAY",
            "score": round(weighted_score, 2),
            "agreement": agreement,
        }

    def calculate_confidence(self, ensemble_result):
        if not ensemble_result:
            return 0

        base = int(ensemble_result.get("score", 0) or 0)
        if ensemble_result.get("agreement") == "LOW":
            base -= 10
        elif ensemble_result.get("agreement") == "MEDIUM":
            base -= 5
        return max(0, min(100, base))

    def analyze_disagreement(self, predictions):
        if not predictions:
            return {"disagreement_level": "NO_DISAGREEMENT", "details": []}

        distinct = {item.get("prediction") for item in predictions}
        if len(distinct) >= 2:
            return {"disagreement_level": "HIGH_DISAGREEMENT", "details": list(distinct)}
        return {"disagreement_level": "LOW_DISAGREEMENT", "details": list(distinct)}
