class OutcomeTrackingService:

    def record_result(self, game_result):
        if not game_result:
            return {"status": "PENDING"}
        return {
            "status": game_result.get("status", "COMPLETED"),
            "result": game_result.get("result", "UNKNOWN"),
        }

    def update_prediction(self, prediction_id):
        if prediction_id is None:
            return {"status": "PENDING"}
        return {"prediction_id": prediction_id, "status": "UPDATED"}

    def calculate_result(self, prediction, outcome):
        if not prediction or not outcome:
            return {"result": "UNKNOWN", "win": False}
        return {"result": "WIN" if prediction.get("prediction") == outcome.get("result") else "LOSS", "win": prediction.get("prediction") == outcome.get("result")}
