from __future__ import annotations

from datetime import date
from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories import game_repository
from app.services.model_evaluation_service import ModelEvaluationService
from app.services.weight_optimization_service import WeightOptimizationService


class BacktestingService:

    SUPPORTED_MARKETS = {"moneyline", "spread", "total"}

    def __init__(
        self,
        evaluation_service=None,
        weight_optimization_service=None,
    ):
        self.evaluation_service = (
            evaluation_service or ModelEvaluationService()
        )
        self.weight_optimization_service = (
            weight_optimization_service or WeightOptimizationService()
        )

    def run_backtest(
        self,
        model_version,
        start_date,
        end_date,
        sport: str | None = None,
        market: str = "moneyline",
        db: Session | None = None,
        games: list | None = None,
        model=None,
        weight_profile: dict | None = None,
    ):
        normalized_market = (market or "moneyline").strip().lower()
        if normalized_market not in self.SUPPORTED_MARKETS:
            raise ValueError("Unsupported market")

        historical_games = list(games or self._load_games(db, start_date, end_date, sport))
        predictions = self.simulate_predictions(
            historical_games,
            model or model_version,
            model_version=model_version,
            market=normalized_market,
            weight_profile=weight_profile,
        )
        results = self.calculate_results(predictions)
        report = self.generate_report(results)

        return {
            "model": model_version,
            "sport": sport,
            "market": normalized_market,
            "start_date": self._date_value(start_date),
            "end_date": self._date_value(end_date),
            "weight_profile": weight_profile,
            "games": len(historical_games),
            "predictions": predictions,
            "results": results,
            "report": report,
            "recommendation": report["recommendation"],
        }

    def simulate_predictions(
        self,
        games,
        model,
        *,
        model_version: str | None = None,
        market: str = "moneyline",
        weight_profile: dict | None = None,
    ):
        predictions = []

        for game in games or []:
            try:
                historical_inputs = self._historical_snapshot(game)
                predicted = self._predict_game(
                    game=game,
                    historical_inputs=historical_inputs,
                    model=model,
                    model_version=model_version,
                )

                predictions.append(
                    {
                        "game_id": self._read(game, ("id",), default=None),
                        "sport": self._read(game, ("sport",), default=None),
                        "market": market,
                        "predicted_winner": predicted["winner"],
                        "confidence": predicted["confidence"],
                        "actual_winner": self._actual_winner(game),
                        "historical_inputs": historical_inputs,
                        "used_weight_profile": weight_profile,
                        "future_data_excluded": self._future_data_excluded(game, historical_inputs),
                        "bet_outcome": self._bet_outcome(game, predicted["winner"], market),
                    }
                )
            except Exception as exc:
                predictions.append(
                    {
                        "game_id": self._read(game, ("id",), default=None),
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        return predictions

    def calculate_results(
        self,
        predictions,
    ):
        successful = [item for item in predictions if item.get("status") != "failed"]
        evaluated = [item for item in successful if item.get("actual_winner") is not None]

        games_tested = len(evaluated)
        correct = sum(1 for item in evaluated if item.get("predicted_winner") == item.get("actual_winner"))
        confidence_accuracy = round(
            sum(item.get("confidence", 0.0) for item in evaluated if item.get("predicted_winner") == item.get("actual_winner"))
            / max(correct, 1),
            2,
        ) if correct else 0.0

        calibration_error = 0.0
        if evaluated:
            calibration_error = round(
                sum(
                    abs(float(item.get("confidence", 50.0)) - (100.0 if item.get("predicted_winner") == item.get("actual_winner") else 0.0))
                    for item in evaluated
                ) / games_tested,
                2,
            )

        ats_wins = sum(1 for item in evaluated if item.get("bet_outcome") == "win")
        ats_losses = sum(1 for item in evaluated if item.get("bet_outcome") == "loss")

        cumulative_units = 0.0
        peak_units = 0.0
        max_drawdown = 0.0
        for item in evaluated:
            cumulative_units += self._units_from_outcome(item.get("bet_outcome"))
            peak_units = max(peak_units, cumulative_units)
            max_drawdown = max(max_drawdown, round(peak_units - cumulative_units, 2))

        units = round(sum(self._units_from_outcome(item.get("bet_outcome")) for item in evaluated), 2)
        roi = round((units / games_tested) * 100.0, 2) if games_tested else 0.0
        accuracy = round((correct / games_tested) * 100.0, 2) if games_tested else 0.0

        return {
            "games_tested": games_tested,
            "correct_predictions": correct,
            "accuracy": accuracy,
            "confidence_accuracy": confidence_accuracy,
            "calibration_error": calibration_error,
            "ats_record": f"{ats_wins}-{ats_losses}",
            "win_pct": round((ats_wins / games_tested) * 100.0, 2) if games_tested else 0.0,
            "units": units,
            "roi": roi,
            "max_drawdown": max_drawdown,
            "failed_simulations": len(predictions) - len(successful),
        }

    def generate_report(
        self,
        results,
    ):
        recommendation = "hold"
        if (
            results["games_tested"] >= 1
            and results["accuracy"] >= 52.0
            and results["roi"] >= 0.0
            and results["calibration_error"] <= 35.0
        ):
            recommendation = "promote"
        elif results["failed_simulations"]:
            recommendation = "review"

        return {
            "games": results["games_tested"],
            "accuracy": results["accuracy"],
            "roi": results["roi"],
            "calibration_error": results["calibration_error"],
            "recommendation": recommendation,
            "summary": (
                f"Games Tested: {results['games_tested']}, "
                f"ATS: {results['ats_record']}, "
                f"ROI: {results['roi']}%"
            ),
        }

    def _load_games(self, db: Session | None, start_date, end_date, sport: str | None):
        if db is None:
            return []

        rows = game_repository.get_completed_games(db, limit=100000)
        return [
            game
            for game in rows
            if self._within_window(self._read(game, ("game_date",), default=None), start_date, end_date)
            and (sport is None or str(self._read(game, ("sport",), default="")).lower() == str(sport).lower())
        ]

    def _historical_snapshot(self, game):
        historical_inputs = {}
        for key, value in self._to_mapping(game).items():
            lowered = str(key).lower()
            if lowered in {
                "home_score",
                "away_score",
                "winner_team_id",
                "final_score",
                "future_rankings",
                "future_performance",
            }:
                continue
            historical_inputs[key] = value
        return historical_inputs

    def _predict_game(self, *, game, historical_inputs, model, model_version: str | None):
        if isinstance(model, str):
            payload = self.evaluation_service._prediction_for_model(game, model_version or model)
            return {
                "winner": payload.get("winner"),
                "confidence": round(float(payload.get("confidence", 50.0) or 50.0), 2),
            }

        if hasattr(model, "predict") and callable(model.predict):
            payload = model.predict(historical_inputs)
        elif callable(model):
            payload = model(historical_inputs)
        else:
            payload = {
                "winner": self._read(game, ("home_team_id", "home_team", "home"), default=None),
                "confidence": 50.0,
            }

        if not isinstance(payload, dict):
            raise ValueError("model predictions must be dictionaries")

        return {
            "winner": payload.get("winner") or payload.get("predicted_winner") or payload.get("prediction"),
            "confidence": round(float(payload.get("confidence", 50.0) or 50.0), 2),
        }

    def _actual_winner(self, game):
        winner = self._read(game, ("actual_winner", "winner", "winner_team_id"), default=None)
        if winner is not None:
            return winner

        home_score = self._read(game, ("home_score",), default=None)
        away_score = self._read(game, ("away_score",), default=None)
        if home_score is None or away_score is None:
            return None

        home_team_id = self._read(game, ("home_team_id", "home_team", "home"), default=None)
        away_team_id = self._read(game, ("away_team_id", "away_team", "away"), default=None)
        return home_team_id if float(home_score) >= float(away_score) else away_team_id

    def _bet_outcome(self, game, predicted_winner, market: str):
        actual_winner = self._actual_winner(game)
        if actual_winner is None or predicted_winner is None:
            return "push"

        if market == "moneyline":
            return "win" if str(predicted_winner) == str(actual_winner) else "loss"

        explicit = self._read(game, ("bet_outcome", f"{market}_outcome"), default=None)
        if explicit is not None:
            return str(explicit)

        return "win" if str(predicted_winner) == str(actual_winner) else "loss"

    def _units_from_outcome(self, outcome):
        normalized = str(outcome or "push").lower()
        if normalized == "win":
            return 1.0
        if normalized == "loss":
            return -1.0
        return 0.0

    def _future_data_excluded(self, game, historical_inputs: dict):
        raw = self._to_mapping(game)
        blocked_keys = {"final_score", "future_rankings", "future_performance", "home_score", "away_score"}
        present = blocked_keys.intersection({str(key).lower() for key in raw.keys()})
        retained = blocked_keys.intersection({str(key).lower() for key in historical_inputs.keys()})
        return bool(present) and not retained or not present

    def _within_window(self, value, start_date, end_date):
        if value is None:
            return False

        current_date = self._date_value(value)
        start = self._date_value(start_date)
        end = self._date_value(end_date)
        return start <= current_date <= end

    def _date_value(self, value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value).date()
        raise ValueError("date values must be date-like")

    def _read(self, obj, keys, default=None):
        mapping = self._to_mapping(obj)
        for key in keys:
            if key in mapping:
                return mapping[key]
            if hasattr(obj, key):
                return getattr(obj, key)
        return default

    def _to_mapping(self, obj):
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "__dict__"):
            return {
                key: value
                for key, value in vars(obj).items()
                if not key.startswith("_")
            }
        return {}
