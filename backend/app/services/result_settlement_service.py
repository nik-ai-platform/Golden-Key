from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult


class ResultSettlementService:

    DEFAULT_STAKE = 100.0
    TIE_CAPABLE_SPORTS = {"SOCCER", "RUGBY"}
    TIE_CAPABLE_LEAGUES = {"NFL"}

    def settle_game(
        self,
        db: Session,
        game_id: int,
    ) -> dict:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")
        if game.home_score is None or game.away_score is None:
            raise ValueError(f"Game {game_id} has no final score")

        predictions = (
            db.query(Prediction)
            .filter(Prediction.game_id == game_id)
            .all()
        )
        if not predictions:
            return {
                "game_id": game_id,
                "settled": 0,
                "results": [],
            }

        results = []
        for prediction in predictions:
            existing = (
                db.query(PredictionResult)
                .filter(PredictionResult.prediction_id == prediction.id)
                .first()
            )
            if existing:
                results.append(
                    {
                        "prediction_id": prediction.id,
                        "status": "already_settled",
                        "outcome": existing.outcome,
                    }
                )
                continue

            graded = self.grade_prediction(
                db=db,
                game=game,
                prediction=prediction,
            )
            db.add(
                PredictionResult(
                    prediction_id=prediction.id,
                    actual_result=graded["actual_result"],
                    predicted_result=graded["predicted_result"],
                    outcome=graded["outcome"],
                    profit_loss=graded["profit_loss"],
                )
            )
            results.append(
                {
                    "prediction_id": prediction.id,
                    "market": prediction.market,
                    "result": graded["outcome"],
                    "outcome": graded["outcome"],
                    "profit_loss": graded["profit_loss"],
                }
            )

        db.commit()
        return {
            "game_id": game_id,
            "settled": sum(
                item.get("status") != "already_settled"
                for item in results
            ),
            "results": results,
        }

    def regrade_prediction(
        self,
        db: Session,
        prediction_id: int,
    ) -> PredictionResult:
        prediction = db.get(Prediction, prediction_id)
        if prediction is None:
            raise ValueError(f"Prediction {prediction_id} not found")
        game = db.get(Game, prediction.game_id)
        if game is None:
            raise ValueError(f"Game {prediction.game_id} not found")
        if game.home_score is None or game.away_score is None:
            raise ValueError(f"Game {game.id} has no final score")

        graded = self.grade_prediction(
            db=db,
            game=game,
            prediction=prediction,
        )
        result = (
            db.query(PredictionResult)
            .filter(PredictionResult.prediction_id == prediction.id)
            .one_or_none()
        )
        if result is None:
            result = PredictionResult(prediction_id=prediction.id)
            db.add(result)

        result.actual_result = graded["actual_result"]
        result.predicted_result = graded["predicted_result"]
        result.outcome = graded["outcome"]
        result.profit_loss = graded["profit_loss"]
        db.commit()
        db.refresh(result)
        return result

    def grade_prediction(
        self,
        db: Session,
        game: Game,
        prediction: Prediction,
    ) -> dict:
        market = (prediction.market or "").lower()
        if market in {"spread", "ats"}:
            return self._grade_spread(game, prediction)
        if market in {"moneyline", "ml"}:
            return self._grade_moneyline(game, prediction)
        if market in {"total", "totals", "over_under"}:
            return self._grade_total(game, prediction)
        raise ValueError(f"Unsupported market: {prediction.market}")

    def _grade_moneyline(
        self,
        game: Game,
        prediction: Prediction,
    ) -> dict:
        home_score = float(game.home_score)
        away_score = float(game.away_score)
        selection = (prediction.selection or "").upper()

        if home_score == away_score:
            if not self._game_allows_tie(game):
                raise ValueError(
                    f"Game {game.id} cannot have a tied moneyline result"
                )
            outcome = "PUSH"
        elif selection == "HOME":
            outcome = "WIN" if home_score > away_score else "LOSS"
        elif selection == "AWAY":
            outcome = "WIN" if away_score > home_score else "LOSS"
        else:
            raise ValueError(
                "Unsupported moneyline selection: "
                f"{prediction.selection}"
            )

        american_odds = self._snapshot_price(prediction)
        return {
            "predicted_result": selection,
            "actual_result": (
                "HOME"
                if home_score > away_score
                else "AWAY"
                if away_score > home_score
                else "TIE"
            ),
            "outcome": outcome,
            "profit_loss": self.calculate_profit_loss(
                outcome=outcome,
                american_odds=american_odds,
            ),
        }

    def _grade_spread(
        self,
        game: Game,
        prediction: Prediction,
    ) -> dict:
        selection = (prediction.selection or "").upper()
        if selection == "PASS":
            return {
                "predicted_result": "PASS",
                "actual_result": "NO_BET",
                "outcome": "PUSH",
                "profit_loss": 0.0,
            }
        spread = getattr(prediction, "line_value", None)
        if spread is None:
            raise ValueError(
                f"Prediction {prediction.id} has no spread line snapshot"
            )
        if selection == "HOME":
            selected_score = float(game.home_score)
            opponent_score = float(game.away_score)
        elif selection == "AWAY":
            selected_score = float(game.away_score)
            opponent_score = float(game.home_score)
        else:
            raise ValueError(
                f"Unsupported spread selection: {prediction.selection}"
            )
        spread = float(spread)
        adjusted_score = selected_score + spread
        outcome = (
            "WIN"
            if adjusted_score > opponent_score
            else "LOSS"
            if adjusted_score < opponent_score
            else "PUSH"
        )
        return {
            "predicted_result": f"{selection} {spread:+g}",
            "actual_result": f"{game.home_score}-{game.away_score}",
            "outcome": outcome,
            "profit_loss": self.calculate_profit_loss(
                outcome=outcome,
                american_odds=self._snapshot_price(prediction),
            ),
        }

    def _grade_total(
        self,
        game: Game,
        prediction: Prediction,
    ) -> dict:
        line_value = getattr(prediction, "line_value", None)
        if line_value is None:
            raise ValueError(
                f"Prediction {prediction.id} has no total line snapshot"
            )
        total_line = float(line_value)
        final_total = float(game.home_score) + float(game.away_score)
        selection = (prediction.selection or "").upper()
        if selection == "OVER":
            outcome = (
                "WIN"
                if final_total > total_line
                else "LOSS"
                if final_total < total_line
                else "PUSH"
            )
        elif selection == "UNDER":
            outcome = (
                "WIN"
                if final_total < total_line
                else "LOSS"
                if final_total > total_line
                else "PUSH"
            )
        else:
            raise ValueError(
                f"Unsupported total selection: {prediction.selection}"
            )

        return {
            "predicted_result": f"{selection} {total_line}",
            "actual_result": str(final_total),
            "outcome": outcome,
            "profit_loss": self.calculate_profit_loss(
                outcome=outcome,
                american_odds=self._snapshot_price(prediction),
            ),
        }

    def _snapshot_price(
        self,
        prediction: Prediction,
    ) -> int:
        american_odds = getattr(prediction, "american_odds", None)
        if american_odds is None:
            raise ValueError(
                f"Prediction {prediction.id} has no American odds snapshot"
            )
        return int(american_odds)

    def _game_allows_tie(self, game: Game) -> bool:
        sport = str(getattr(game, "sport", "") or "").upper()
        league = str(getattr(game, "league", "") or "").upper()
        return (
            sport in self.TIE_CAPABLE_SPORTS
            or league in self.TIE_CAPABLE_LEAGUES
        )

    def calculate_profit_loss(
        self,
        outcome: str,
        american_odds: int | None,
        stake: float | None = None,
    ) -> float:
        stake = stake if stake is not None else self.DEFAULT_STAKE
        outcome = outcome.upper()
        if outcome == "LOSS":
            return round(-stake, 2)
        if outcome == "PUSH":
            return 0.0
        if outcome != "WIN":
            return 0.0

        american_odds = american_odds or -110
        if american_odds > 0:
            profit = stake * american_odds / 100
        else:
            profit = stake * 100 / abs(american_odds)
        return round(profit, 2)
