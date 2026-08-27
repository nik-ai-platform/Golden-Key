from collections import defaultdict
from datetime import date
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.backtest_result import BacktestResult
from app.models.game import Game
from app.models.odds import Odds
from app.services.prediction_engine import PredictionEngine


class BacktestEngine:

    def __init__(
        self,
        prediction_engine: PredictionEngine | None = None,
    ):
        self.prediction_engine = prediction_engine or PredictionEngine()

    def run(
        self,
        db: Session,
        model_version: str,
        start_date: date,
        end_date: date,
        sport: str | None = None,
        market: str = "spread",
    ) -> dict:
        market = str(market or "spread").lower()
        if market not in {"moneyline", "spread"}:
            raise ValueError("BacktestEngine currently supports moneyline and spread markets")

        run_id = self._next_backtest_id(db)
        games = self._load_games(db, start_date, end_date, sport)
        rows: list[BacktestResult] = []
        edges: list[float] = []

        for historical_game in games:
            odds = (
                db.query(Odds)
                .filter(Odds.game_id == historical_game.id)
                .order_by(Odds.created_at.desc(), Odds.id.desc())
                .first()
            )
            if not odds:
                continue

            try:
                prediction = self.prediction_engine.analyze_game(
                    db, historical_game.id, persist=False
                )
            except Exception:
                continue

            predicted_side = self._predicted_side(historical_game, prediction)
            actual_side = self._actual_side(historical_game, odds, market)
            win_loss = self._grade(predicted_side, actual_side, market)
            profit_loss = self._profit_loss(win_loss)

            edge_value = float(getattr(prediction, "projected_edge", 0.0) or 0.0)
            edges.append(edge_value)

            row = BacktestResult(
                backtest_id=run_id,
                model_version=model_version,
                sport=sport,
                start_date=start_date,
                end_date=end_date,
                game_id=historical_game.id,
                predicted_side=predicted_side,
                actual_side=actual_side,
                spread=float(odds.spread_home or 0.0),
                npi_score=float(getattr(prediction, "npi_score", 0.0) or 0.0),
                confidence=float(getattr(prediction, "confidence_score", 0.0) or 0.0),
                win_loss=win_loss,
                market=market,
                outcome=win_loss,
                profit_loss=profit_loss,
            )
            rows.append(row)

        if rows:
            db.add_all(rows)
            db.commit()

        stats = self.calculate_statistics(rows, edges)
        return {
            "backtest_id": run_id,
            "model_version": model_version,
            "sport": sport,
            "market": market,
            "start_date": start_date,
            "end_date": end_date,
            "stats": stats,
            "games_stored": len(rows),
        }

    def run_summaries(self, db: Session) -> list[dict]:
        run_ids = [
            value[0]
            for value in (
                db.query(BacktestResult.backtest_id)
                .filter(BacktestResult.backtest_id.is_not(None))
                .distinct()
                .order_by(BacktestResult.backtest_id.desc())
                .all()
            )
        ]
        return [self.run_summary(db, run_id) for run_id in run_ids]

    def run_summary(self, db: Session, backtest_id: int) -> dict:
        rows = (
            db.query(BacktestResult)
            .filter(BacktestResult.backtest_id == backtest_id)
            .order_by(BacktestResult.id.asc())
            .all()
        )
        if not rows:
            return {}

        stats = self.calculate_statistics(rows, [])
        first = rows[0]
        return {
            "id": backtest_id,
            "model": first.model_version,
            "sport": first.sport,
            "start_date": first.start_date.isoformat() if first.start_date else None,
            "end_date": first.end_date.isoformat() if first.end_date else None,
            "games": stats["games_tested"],
            "accuracy": stats["win_pct"],
            "ats_record": stats["ats_record"],
            "roi": stats["roi"],
            "stats": stats,
            "results": [
                {
                    "id": row.id,
                    "game_id": row.game_id,
                    "predicted_side": row.predicted_side,
                    "actual_side": row.actual_side,
                    "spread": row.spread,
                    "npi_score": row.npi_score,
                    "confidence": row.confidence,
                    "win_loss": row.win_loss,
                    "profit_loss": row.profit_loss,
                }
                for row in rows
            ],
        }

    def version_comparison(self, db: Session) -> list[dict]:
        grouped = defaultdict(list)
        rows = db.query(BacktestResult).filter(BacktestResult.backtest_id.is_not(None)).all()
        for row in rows:
            grouped[str(row.model_version or "unknown")].append(row)

        comparison = []
        for model, model_rows in grouped.items():
            stats = self.calculate_statistics(model_rows, edges=[])
            comparison.append(
                {
                    "model": model,
                    "ats": stats["win_pct"],
                    "roi": stats["roi"],
                    "avg_confidence": stats["average_confidence"],
                }
            )
        comparison.sort(key=lambda item: item["ats"], reverse=True)
        return comparison

    def calculate_statistics(self, rows: list[BacktestResult], edges: list[float]) -> dict:
        games_tested = len(rows)
        wins = sum(1 for value in rows if str(value.win_loss or "").upper() == "WIN")
        losses = sum(1 for value in rows if str(value.win_loss or "").upper() == "LOSS")
        pushes = games_tested - wins - losses
        win_pct = round((wins / games_tested) * 100.0, 2) if games_tested else 0.0

        roi = 0.0
        if games_tested:
            total_profit = sum(float(value.profit_loss or 0.0) for value in rows)
            roi = round((total_profit / games_tested) * 100.0, 2)

        avg_npi = round(sum(float(value.npi_score or 0.0) for value in rows) / games_tested, 2) if games_tested else 0.0
        avg_conf = round(sum(float(value.confidence or 0.0) for value in rows) / games_tested, 2) if games_tested else 0.0
        avg_edge = round(sum(edges) / len(edges), 2) if edges else 0.0

        streak_win = 0
        streak_loss = 0
        current_win = 0
        current_loss = 0
        for value in rows:
            result = str(value.win_loss or "").upper()
            if result == "WIN":
                current_win += 1
                current_loss = 0
            elif result == "LOSS":
                current_loss += 1
                current_win = 0
            else:
                current_win = 0
                current_loss = 0
            streak_win = max(streak_win, current_win)
            streak_loss = max(streak_loss, current_loss)

        return {
            "games_tested": games_tested,
            "ats_record": f"{wins}-{losses}",
            "moneyline_record": f"{wins}-{losses}",
            "totals_record": f"{wins}-{losses}-{pushes}",
            "win_pct": win_pct,
            "roi": roi,
            "average_edge": avg_edge,
            "average_npi": avg_npi,
            "average_confidence": avg_conf,
            "largest_winning_streak": streak_win,
            "largest_losing_streak": streak_loss,
        }

    def _next_backtest_id(self, db: Session) -> int:
        current = db.query(func.max(BacktestResult.backtest_id)).scalar()
        return int(current or 0) + 1

    def _load_games(self, db: Session, start_date: date, end_date: date, sport: str | None) -> list[Game]:
        query = db.query(Game).filter(Game.winner_team_id.is_not(None))
        query = query.filter(Game.game_date >= datetime.combine(start_date, datetime.min.time()))
        query = query.filter(Game.game_date <= datetime.combine(end_date, datetime.max.time()))
        if sport:
            query = query.filter(func.lower(Game.sport) == str(sport).lower())
        return query.order_by(Game.game_date.asc()).all()

    def _actual_side(self, game: Game, odds: Odds, market: str) -> str:
        market = str(market or "spread").lower()

        if game.home_score is None or game.away_score is None:
            return "PUSH"

        if market == "moneyline":
            if game.winner_team_id is None:
                return "PUSH"
            if game.winner_team_id == game.home_team_id:
                return "HOME"
            if game.winner_team_id == game.away_team_id:
                return "AWAY"
            return "PUSH"

        if market == "spread":
            home_margin = float(game.home_score) - float(game.away_score)
            spread = float(odds.spread_home or 0.0)
            covered_margin = home_margin + spread
            if covered_margin > 0:
                return "HOME"
            if covered_margin < 0:
                return "AWAY"
            return "PUSH"

        raise ValueError(f"Unsupported backtest market: {market}")

    def _predicted_side(self, game: Game, prediction) -> str:
        raw = str(getattr(prediction, "selection", "") or "").strip().upper()
        if raw in {"HOME", "H", "FAVORITE"}:
            return "HOME"
        if raw in {"AWAY", "A", "DOG", "UNDERDOG"}:
            return "AWAY"

        home_name = str(getattr(game.home_team, "name", "") or "").strip().upper()
        away_name = str(getattr(game.away_team, "name", "") or "").strip().upper()
        if raw and home_name and home_name in raw:
            return "HOME"
        if raw and away_name and away_name in raw:
            return "AWAY"
        return "PASS"

    def _grade(self, predicted_side: str, actual_side: str, market: str) -> str:
        if predicted_side == "PASS" or actual_side == "PUSH":
            return "PUSH"
        return "WIN" if predicted_side == actual_side else "LOSS"

    def _profit_loss(self, win_loss: str) -> float:
        if win_loss == "WIN":
            return 1.0
        if win_loss == "LOSS":
            return -1.0
        return 0.0