from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.schemas.prediction import PredictionCreate
from app.services.ai_analysis_engine import (
    AIAnalysisEngine
)
from app.services import ai_analysis_service
from app.services.npi_engine import NPIEngine
from app.services.model_runtime_service import ModelRuntimeService
from app.services.odds_service import NoCompleteOddsSnapshotError
from app.services.simulation_engine import SimulationEngine
from app.services import prediction_service
from app.services.model_evaluation import (
    save_factor_result
)


class PredictionEngine:

    npi_engine = NPIEngine()
    model_runtime = ModelRuntimeService()
    simulation_engine = SimulationEngine()
    ai_engine = AIAnalysisEngine()

    MODEL_VERSION = "NPI-4.0"
    MARKETS = ("spread", "moneyline", "total")
    SPORT_TOTAL_BASELINES = {
        "NFL": 44.5,
        "NCAAF": 52.0,
        "NBA": 224.0,
        "WNBA": 164.0,
        "NCAAB": 145.0,
    }

    def analyze_game(
        self,
        db: Session,
        game_id: int,
        *,
        persist: bool = True,
    ):

        predictions = self.analyze_markets(
            db=db,
            game_id=game_id,
            persist=persist,
        )
        return next(
            prediction
            for prediction in predictions
            if prediction.market == "spread"
        )

    def analyze_markets(
        self,
        db: Session,
        game_id: int,
        *,
        persist: bool = True,
    ):

        game = (
            db.query(Game)
            .filter(
                Game.id == game_id
            )
            .first()
        )

        if not game:
            raise ValueError(
                "Game not found"
            )

        sport = getattr(game, "sport", None)

        if not sport:
            raise ValueError(
                f"Game {game.id} has no sport configured"
            )

        sport = str(sport).upper()

        try:
            runtime_model = self.model_runtime.resolve(
                db=db,
                sport=sport,
            )
            model_version = runtime_model["model_version"]
        except ValueError as error:
            if "No production model configured for sport:" not in str(error):
                raise
            model_version = self.MODEL_VERSION

        existing_by_market = {}
        if persist:
            existing_predictions = (
                db.query(Prediction)
                .filter(
                    Prediction.game_id == game_id,
                    Prediction.model_version == model_version,
                    Prediction.market.in_(self.MARKETS),
                )
                .all()
            )
            existing_by_market = {
                prediction.market: prediction
                for prediction in existing_predictions
            }
            if all(market in existing_by_market for market in self.MARKETS):
                return [
                    existing_by_market[market]
                    for market in self.MARKETS
                ]

        odds = (
            db.query(Odds)
            .filter(
                Odds.game_id == game_id,
                Odds.spread_home.is_not(None),
                Odds.spread_away.is_not(None),
                Odds.moneyline_home.is_not(None),
                Odds.moneyline_away.is_not(None),
                Odds.total.is_not(None),
            )
            .order_by(Odds.id.desc())
            .first()
        )

        if not odds:
            raise NoCompleteOddsSnapshotError(
                "No complete odds snapshot"
            )

        required_odds = (
            odds.spread_home,
            odds.spread_away,
            odds.moneyline_home,
            odds.moneyline_away,
            odds.total,
        )
        if any(value is None for value in required_odds):
            raise ValueError(
                "Complete spread, moneyline, and total odds are required"
            )

        npi_result = self.npi_engine.calculate(
            db=db,
            game=game,
            odds=odds,
            sport=sport,
            model_version=model_version,
        )

        specifications = self._market_specifications(
            sport=sport,
            odds=odds,
            spread_npi=npi_result,
        )
        for specification in specifications:
            specification.update(
                {
                    "odds_snapshot_id": odds.id,
                    "sportsbook": odds.sportsbook,
                    "odds_observed_at": odds.created_at,
                }
            )
        results = []

        for specification in specifications:
            market = specification["market"]
            existing = existing_by_market.get(market)
            if existing is not None:
                results.append(existing)
                continue

            factors = specification.pop("factors")
            analysis = self.ai_engine.generate_analysis(
                {
                    "npi_score": specification["npi_score"],
                    "simulation_probability": specification[
                        "simulation_probability"
                    ],
                    "confidence_score": specification[
                        "confidence_score"
                    ],
                    "factors": factors,
                }
            )
            prediction = PredictionCreate(
                game_id=game_id,
                model_version=model_version,
                reasoning=(
                    f"{market.title()} model. "
                    f"{analysis['explanation']}"
                ),
                **specification,
            )

            if not persist:
                from types import SimpleNamespace

                results.append(SimpleNamespace(**prediction.model_dump()))
                continue

            created_prediction = prediction_service.create_prediction(
                db,
                prediction,
            )
            ai_analysis_service.create_analysis(
                db,
                created_prediction.id,
                analysis,
            )
            for factor in factors:
                save_factor_result(
                    db=db,
                    prediction_id=created_prediction.id,
                    factor_name=factor["name"],
                    weight=factor["weight"],
                    factor_score=factor["score"],
                    predicted_side=prediction.selection,
                )
            results.append(created_prediction)

        return sorted(
            results,
            key=lambda item: self.MARKETS.index(item.market),
        )

    def _market_specifications(self, sport, odds, spread_npi):
        spread_score = spread_npi["npi_score"]
        spread_simulation = self.simulation_engine.simulate(
            npi_score=spread_score,
            spread=odds.spread_home,
        )
        spread_edge = self.calculate_edge(
            spread_simulation["win_probability"],
            odds,
        )
        spread_selection = self.determine_pick(None, odds, spread_edge)

        moneyline = self._moneyline_specification(
            odds=odds,
            spread_npi=spread_score,
        )
        total = self._total_specification(
            sport=sport,
            odds=odds,
        )

        spread_confidence = self.calculate_confidence(
            spread_score,
            spread_edge,
            spread_simulation,
        )
        return [
            {
                "market": "spread",
                "selection": spread_selection,
                "line_value": (
                    odds.spread_home
                    if spread_selection != "AWAY"
                    else odds.spread_away
                ),
                "american_odds": -110,
                "npi_score": spread_score,
                "win_probability": spread_simulation["win_probability"],
                "simulation_probability": spread_simulation[
                    "win_probability"
                ],
                "simulation_runs": spread_simulation["runs"],
                "simulation_margin": spread_simulation["average_margin"],
                "confidence_score": spread_confidence,
                "projected_edge": spread_edge,
                "risk_level": self.calculate_risk(
                    spread_confidence,
                    spread_edge,
                ),
                "factors": spread_npi["factors"],
            },
            moneyline,
            total,
        ]

    def _moneyline_specification(self, odds, spread_npi):
        home_implied = self._american_implied_probability(
            odds.moneyline_home
        )
        away_implied = self._american_implied_probability(
            odds.moneyline_away
        )
        implied_total = home_implied + away_implied
        fair_home = home_implied / implied_total * 100

        simulation = self.simulation_engine.simulate(
            npi_score=spread_npi,
            spread=0,
        )
        home_probability = simulation["win_probability"]
        home_edge = home_probability - fair_home
        if abs(home_edge) < 3:
            selection = "PASS"
        else:
            selection = "HOME" if home_edge > 0 else "AWAY"
        selected_probability = (
            home_probability if selection != "AWAY" else 100 - home_probability
        )
        selected_edge = abs(home_edge)
        npi_score = self._bounded_npi(100 + selected_edge * 2)
        confidence = self.calculate_confidence(
            npi_score,
            selected_edge,
            {**simulation, "win_probability": selected_probability},
        )
        return {
            "market": "moneyline",
            "selection": selection,
            "line_value": None,
            "american_odds": (
                odds.moneyline_home
                if selection != "AWAY"
                else odds.moneyline_away
            ),
            "npi_score": npi_score,
            "win_probability": round(selected_probability, 2),
            "simulation_probability": round(selected_probability, 2),
            "simulation_runs": simulation["runs"],
            "simulation_margin": simulation["average_margin"],
            "confidence_score": confidence,
            "projected_edge": round(selected_edge, 2),
            "risk_level": self.calculate_risk(confidence, selected_edge),
            "factors": [
                {
                    "name": "Moneyline Value",
                    "weight": 200,
                    "score": npi_score,
                    "explanation": (
                        f"Model probability {home_probability:.2f}% versus "
                        f"vig-free home probability {fair_home:.2f}%"
                    ),
                }
            ],
        }

    def _total_specification(self, sport, odds):
        baseline = self.SPORT_TOTAL_BASELINES.get(sport, float(odds.total))
        posted_total = float(odds.total)
        projected_total = baseline + (posted_total - baseline) * 0.25
        total_edge = projected_total - posted_total
        if abs(total_edge) < 2:
            selection = "PASS"
        else:
            selection = "OVER" if total_edge > 0 else "UNDER"
        probability = min(75.0, 50.0 + abs(total_edge) * 3)
        npi_score = self._bounded_npi(100 + abs(total_edge) * 5)
        simulation = {
            "win_probability": round(probability, 2),
            "runs": 0,
            "average_margin": round(total_edge, 2),
        }
        confidence = self.calculate_confidence(
            npi_score,
            total_edge,
            simulation,
        )
        return {
            "market": "total",
            "selection": selection,
            "line_value": posted_total,
            "american_odds": -110,
            "npi_score": npi_score,
            "win_probability": round(probability, 2),
            "simulation_probability": round(probability, 2),
            "simulation_runs": 0,
            "simulation_margin": round(total_edge, 2),
            "confidence_score": confidence,
            "projected_edge": round(total_edge, 2),
            "risk_level": self.calculate_risk(confidence, total_edge),
            "factors": [
                {
                    "name": "Total Environment",
                    "weight": 200,
                    "score": npi_score,
                    "explanation": (
                        f"Projected total {projected_total:.2f} versus "
                        f"posted total {posted_total:.2f}"
                    ),
                }
            ],
        }

    def _american_implied_probability(self, american_odds):
        price = float(american_odds)
        if price < 0:
            return abs(price) / (abs(price) + 100) * 100
        return 100 / (price + 100) * 100

    def _bounded_npi(self, score):
        return round(max(0.0, min(float(score), 200.0)), 2)

    def calculate_npi(
        self,
        game,
        odds,
    ):

        score = 50

        score += 10

        if abs(odds.spread_home) <= 5:
            score += 10

        score = min(
            max(score, 0),
            100,
        )

        return score

    def calculate_probability(
        self,
        npi_score,
    ):

        return round(
            50 + (npi_score - 50) * 0.8,
            2,
        )

    def calculate_edge(
        self,
        probability,
        odds,
    ):

        market_probability = 50

        return round(
            probability - market_probability,
            2,
        )

    def calculate_confidence(
        self,
        npi,
        edge,
        simulation,
    ):

        confidence = (
            (npi / 200) * 40
            +
            (abs(edge) * 2)
            +
            (
                simulation["win_probability"]
                * 0.3
            )
        )

        return round(
            max(
                0,
                min(
                confidence,
                95
                ),
            ),
            2,
        )

    def calculate_risk(
        self,
        confidence,
        edge,
    ):

        if confidence >= 80:
            return "low"

        if confidence >= 65:
            return "medium"

        return "high"

    def determine_pick(
        self,
        game,
        odds,
        edge,
    ):

        if edge > 5:
            return "HOME"

        if edge < -5:
            return "AWAY"

        return "PASS"

    def generate_reasoning(
        self,
        game,
        odds,
        npi,
        edge,
    ):

        return (
            f"NPI Score: {npi}. "
            f"Projected market edge: {edge}%. "
            "Recommendation generated from "
            "team strength, market value, "
            "and spread analysis."
        )
