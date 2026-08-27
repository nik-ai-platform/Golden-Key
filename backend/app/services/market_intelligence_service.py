from __future__ import annotations

from typing import Any

from app.models.market_value import MarketValue
from app.repositories import odds_repository


class MarketIntelligenceService:

    def calculate_value(
        self,
        prediction,
        market,
    ):
        prediction_payload = prediction or {}
        market_payload = market or {}

        spread_edge = self.calculate_spread_edge(
            prediction_payload.get("predicted_margin"),
            market_payload.get("sportsbook_spread"),
        )
        moneyline_edge = self.calculate_moneyline_value(
            prediction_payload.get("win_probability"),
            market_payload.get("odds"),
        )
        total_edge = self.calculate_total_edge(
            prediction_payload.get("projected_total"),
            market_payload.get("market_total"),
        )

        line_movement = self._line_movement(
            market_payload.get("opening_line"),
            market_payload.get("current_line"),
        )
        confidence = self._bounded(prediction_payload.get("confidence", 50.0), 0.0, 100.0)
        historical_edge = self._bounded(prediction_payload.get("historical_edge", 0.0) + 50.0, 0.0, 100.0)

        model_edge_score = self._bounded(
            max(abs(spread_edge) * 10.0, abs(moneyline_edge) * 6.0, abs(total_edge) * 8.0),
            0.0,
            100.0,
        )
        movement_score = self._bounded(abs(line_movement) * 12.5, 0.0, 100.0)

        value_score = round(
            (model_edge_score * 0.40)
            + (movement_score * 0.25)
            + (confidence * 0.20)
            + (historical_edge * 0.15),
            2,
        )
        value_score = self._bounded(value_score, 0.0, 100.0)

        recommendation = "hold"
        if value_score >= 80:
            recommendation = "strong_value"
        elif value_score >= 65:
            recommendation = "value"

        return {
            "spread_edge": round(spread_edge, 2),
            "moneyline_edge": round(moneyline_edge, 2),
            "total_edge": round(total_edge, 2),
            "line_movement": round(line_movement, 2),
            "value_score": round(value_score, 2),
            "recommendation": recommendation,
        }

    def calculate_spread_edge(
        self,
        predicted_margin,
        sportsbook_spread,
    ):
        if predicted_margin is None or sportsbook_spread is None:
            return 0.0
        return round(abs(float(predicted_margin)) - abs(float(sportsbook_spread)), 2)

    def calculate_moneyline_value(
        self,
        win_probability,
        odds,
    ):
        if win_probability is None or odds is None:
            return 0.0
        implied = self._implied_probability(float(odds))
        return round(float(win_probability) - implied, 2)

    def calculate_total_edge(
        self,
        projected_total,
        market_total,
    ):
        if projected_total is None or market_total is None:
            return 0.0
        return round(float(projected_total) - float(market_total), 2)

    def evaluate_game(self, db, game, prediction) -> dict[str, Any] | None:
        if db is None or not hasattr(db, "query") or game is None:
            return None

        latest_odds = odds_repository.get_latest_odds(db, game.id)
        if latest_odds is None:
            return None

        odds_history = odds_repository.get_odds_history(db, game.id)
        opening = odds_history[0] if odds_history else latest_odds
        closing = odds_history[-1] if odds_history else latest_odds

        home_score = float(getattr(prediction, "home_score", 0.0) or 0.0)
        away_score = float(getattr(prediction, "away_score", 0.0) or 0.0)
        predicted_margin = abs(home_score - away_score)
        projected_total = home_score + away_score

        market = {
            "sportsbook_spread": abs(float(getattr(latest_odds, "spread_home", 0.0) or 0.0)),
            "odds": getattr(latest_odds, "moneyline_home", None),
            "market_total": getattr(latest_odds, "total", None),
            "opening_line": getattr(opening, "spread_home", None),
            "current_line": getattr(latest_odds, "spread_home", None),
            "closing_line": getattr(closing, "spread_home", None),
        }
        prediction_payload = {
            "predicted_margin": predicted_margin,
            "win_probability": float(getattr(prediction, "confidence", 50.0) or 50.0),
            "projected_total": projected_total,
            "confidence": float(getattr(prediction, "confidence", 50.0) or 50.0),
            "historical_edge": 0.0,
        }
        result = self.calculate_value(prediction_payload, market)
        result.update(
            {
                "opening_line": market["opening_line"],
                "current_line": market["current_line"],
                "closing_line": market["closing_line"],
                "market_type": "spread",
                "projected_total": projected_total,
            }
        )
        return result

    def save_market_value(self, db, game_id: int, evaluation: dict[str, Any]):
        if db is None or evaluation is None:
            return None

        row = MarketValue(
            game_id=game_id,
            market_type=evaluation.get("market_type", "spread"),
            model_projection=evaluation.get("projected_total") or evaluation.get("spread_edge"),
            market_line=evaluation.get("current_line"),
            edge=evaluation.get("spread_edge") or evaluation.get("moneyline_edge") or evaluation.get("total_edge"),
            value_score=evaluation.get("value_score"),
        )
        db.add(row)
        return row

    def market_movers(self, db, limit: int = 10):
        if db is None or not hasattr(db, "query"):
            return []

        odds_rows = db.query(type(odds_repository.get_latest_odds(db, 0))).__class__ if False else None
        rows = db.query(__import__("app.models.odds", fromlist=["Odds"]).Odds).order_by(__import__("app.models.odds", fromlist=["Odds"]).Odds.id.asc()).all()
        grouped: dict[int, list] = {}
        for row in rows:
            grouped.setdefault(row.game_id, []).append(row)

        movers = []
        for game_id, history in grouped.items():
            if len(history) < 2:
                continue
            opening = history[0]
            current = history[-1]
            movement = self._line_movement(opening.spread_home, current.spread_home)
            movers.append(
                {
                    "game_id": game_id,
                    "opening_line": opening.spread_home,
                    "current_line": current.spread_home,
                    "movement": round(movement, 2),
                }
            )

        movers.sort(key=lambda item: abs(item["movement"]), reverse=True)
        return movers[:limit]

    def clv_summary(self, db, limit: int = 20):
        if db is None or not hasattr(db, "query"):
            return []

        from app.models.nik_score import NikScore
        from app.models.odds import Odds

        predictions = db.query(NikScore).order_by(NikScore.id.desc()).limit(limit).all()
        summary = []
        for prediction in predictions:
            odds_history = odds_repository.get_odds_history(db, prediction.game_id)
            if not odds_history:
                continue
            opening = odds_history[0]
            closing = odds_history[-1]
            predicted_margin = abs(float(prediction.home_score or 0.0) - float(prediction.away_score or 0.0))
            clv = self.calculate_spread_edge(predicted_margin, abs(float(closing.spread_home or 0.0)))
            summary.append(
                {
                    "game_id": prediction.game_id,
                    "predicted_line": round(predicted_margin, 2),
                    "closing_line": closing.spread_home,
                    "clv": round(clv, 2),
                }
            )
        return summary

    def _implied_probability(self, odds: float):
        if odds < 0:
            return round((abs(odds) / (abs(odds) + 100.0)) * 100.0, 2)
        return round((100.0 / (odds + 100.0)) * 100.0, 2)

    def _line_movement(self, opening_line, current_line):
        if opening_line is None or current_line is None:
            return 0.0
        return float(current_line) - float(opening_line)

    def _bounded(self, value: float, minimum: float, maximum: float):
        return max(minimum, min(maximum, float(value)))
