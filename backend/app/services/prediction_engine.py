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

    def analyze_game(
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

        runtime_model = self.model_runtime.resolve(
            db=db,
            sport=sport,
        )
        model_version = runtime_model["model_version"]

        if persist:
            existing_prediction = (
                db.query(Prediction)
                .filter(
                    Prediction.game_id == game_id,
                    Prediction.model_version == model_version,
                    Prediction.market == "spread",
                )
                .first()
            )
            if existing_prediction:
                return existing_prediction

        odds = (
            db.query(Odds)
            .filter(
                Odds.game_id == game_id
            )
            .first()
        )

        if not odds:
            raise ValueError(
                "Odds not found"
            )

        npi_result = self.npi_engine.calculate(
            db=db,
            game=game,
            odds=odds,
            sport=sport,
            model_version=model_version,
        )

        npi_score = npi_result["npi_score"]

        simulation = self.simulation_engine.simulate(
            npi_score=npi_score,
            spread=odds.spread_home,
        )

        probability = simulation[
            "win_probability"
        ]

        edge = self.calculate_edge(
            probability,
            odds,
        )

        confidence = self.calculate_confidence(
            npi_score,
            edge,
            simulation,
        )

        risk = self.calculate_risk(
            confidence,
            edge,
        )

        selection = self.determine_pick(
            game,
            odds,
            edge,
        )

        analysis = self.ai_engine.generate_analysis(
            {
                "npi_score": npi_score,
                "simulation_probability":
                simulation["win_probability"],
                "confidence_score":
                confidence,
                "factors":
                npi_result["factors"],
            }
        )

        reasoning = analysis["explanation"]

        prediction = PredictionCreate(
            game_id=game_id,
            model_version=model_version,
            market="spread",
            selection=selection,
            npi_score=npi_score,
            win_probability=probability,
            simulation_probability=
            simulation["win_probability"],
            simulation_runs=
            simulation["runs"],
            simulation_margin=
            simulation["average_margin"],
            confidence_score=confidence,
            projected_edge=edge,
            risk_level=risk,
            reasoning=reasoning,
        )

        if not persist:
            from types import SimpleNamespace

            return SimpleNamespace(
                game_id=game_id,
                model_version=model_version,
                market="spread",
                selection=selection,
                npi_score=npi_score,
                win_probability=probability,
                simulation_probability=simulation["win_probability"],
                simulation_runs=simulation["runs"],
                simulation_margin=simulation["average_margin"],
                confidence_score=confidence,
                projected_edge=edge,
                risk_level=risk,
                reasoning=reasoning,
            )

        created_prediction = prediction_service.create_prediction(
            db,
            prediction,
        )

        ai_analysis_service.create_analysis(
            db,
            created_prediction.id,
            analysis,
        )

        for factor in npi_result["factors"]:
            save_factor_result(
                db=db,
                prediction_id=created_prediction.id,
                factor_name=factor["name"],
                weight=factor["weight"],
                factor_score=factor["score"],
                predicted_side=selection
            )

        return created_prediction

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
