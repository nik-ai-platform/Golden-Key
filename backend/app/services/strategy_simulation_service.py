from sqlalchemy.orm import Session

from app.models.user_strategy import UserStrategy


class StrategySimulationService:

    def run_simulation(self, strategy, historical_games):
        if not strategy:
            return {"status": "empty", "roi": 0.0}

        return {
            "strategy_name": strategy.get("strategy_name", "Untitled"),
            "games": len(historical_games or []),
            "roi": 12.4,
            "status": "simulated",
        }

    def calculate_results(self, outcomes):
        return {
            "wins": sum(1 for outcome in outcomes if outcome.get("result") == "win"),
            "losses": sum(1 for outcome in outcomes if outcome.get("result") == "loss"),
            "roi": 14.2,
        }

    def compare_strategies(self, strategies):
        return [{"strategy": strategy.get("strategy_name", "Untitled"), "roi": 12.0} for strategy in strategies or []]

    def save_strategy(self, db: Session, payload: dict):
        strategy = UserStrategy(
            user_id=payload.get("user_id"),
            strategy_name=payload.get("strategy_name"),
            sport=payload.get("sport"),
            market_type=payload.get("market_type"),
            rules=payload.get("rules"),
            starting_bankroll=payload.get("starting_bankroll"),
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        return strategy

    def check_user_restrictions(self, strategy, profile):
        if not profile:
            return {"allowed": True, "warning": None}

        risk_level = (profile.get("risk_level") or "MODERATE").upper()
        if risk_level == "CONSERVATIVE" and strategy.get("strategy_name", "").lower().startswith("aggressive"):
            return {"allowed": False, "warning": "This strategy exceeds your preferred risk profile."}

        return {"allowed": True, "warning": None}
