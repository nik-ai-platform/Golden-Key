class AccuracyService:

    """
    Evaluates Nik AI prediction performance.
    """

    def evaluate_prediction(
        self,
        predicted_winner,
        actual_winner,
        confidence
    ):

        correct = (
            predicted_winner ==
            actual_winner
        )


        accuracy = (
            100
            if correct
            else 0
        )

        return {

            "correct": correct,

            "accuracy": accuracy,

            "confidence": confidence

        }

    def calculate_accuracy_metrics(
        self,
        evaluations
    ):

        if not evaluations:
            return {
                "games_evaluated": 0,
                "correct_predictions": 0,
                "accuracy_percentage": 0,
            }

        correct_predictions = sum(
            1
            for evaluation in evaluations
            if evaluation.correct
        )

        return {
            "games_evaluated": len(evaluations),
            "correct_predictions": correct_predictions,
            "accuracy_percentage": round(
                (correct_predictions / len(evaluations)) * 100,
                2
            ),
        }
