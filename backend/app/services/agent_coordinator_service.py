from __future__ import annotations

from app.agents.market_agent import MarketAgent
from app.agents.portfolio_agent import PortfolioAgent
from app.agents.prediction_agent import PredictionAgent
from app.agents.research_agent import ResearchAgent
from app.agents.risk_agent import RiskAgent
from app.agents.simulation_agent import SimulationAgent
from app.services.agent_conflict_service import AgentConflictService
from app.services.agent_consensus_service import AgentConsensusService
from app.services.agent_debate_service import AgentDebateService
from app.services.agent_explanation_service import AgentExplanationService
from app.services.agent_message_service import AgentMessageService
from app.services.agent_reputation_service import AgentReputationService
from app.services.agent_weighting_service import AgentWeightingService


class AgentCoordinatorService:
    def __init__(self) -> None:
        self.prediction_agent = PredictionAgent()
        self.research_agent = ResearchAgent()
        self.simulation_agent = SimulationAgent()
        self.risk_agent = RiskAgent()
        self.market_agent = MarketAgent()
        self.portfolio_agent = PortfolioAgent()
        self.message_service = AgentMessageService()
        self.debate_service = AgentDebateService()
        self.consensus_service = AgentConsensusService()
        self.reputation_service = AgentReputationService()
        self.weighting_service = AgentWeightingService()
        self.conflict_service = AgentConflictService()
        self.explanation_service = AgentExplanationService()

    def assign_task(self, event: dict):
        return {
            "prediction_agent": self.prediction_agent.analyze(event),
            "research_agent": self.research_agent.analyze(event),
            "simulation_agent": self.simulation_agent.analyze(event),
            "risk_agent": self.risk_agent.analyze(event),
            "market_agent": self.market_agent.analyze(event),
            "portfolio_agent": self.portfolio_agent.analyze(event),
        }

    def collect_results(self, agents: dict):
        self.message_service.send(
            "simulation_agent",
            "risk_agent",
            "High variance due to injury uncertainty",
        )
        debate = self.debate_service.run(
            {
                "prediction_agent": agents.get("prediction_agent", {}).get("pick", "Celtics -4"),
                "risk_agent": agents.get("risk_agent", {}).get("concern", "Line too efficient"),
                "simulation_agent": f"Celtics probability: {agents.get('simulation_agent', {}).get('win_probability', 61)}%",
            }
        )
        conflict = self.conflict_service.detect(
            {
                "prediction_confidence": agents.get("prediction_agent", {}).get("confidence", 78),
                "simulation_confidence": agents.get("simulation_agent", {}).get("win_probability", 61),
            }
        )
        weights = self.weighting_service.update()
        consensus = self.consensus_service.combine(
            {
                "prediction_confidence": agents.get("prediction_agent", {}).get("confidence", 78),
                "simulation_confidence": agents.get("simulation_agent", {}).get("win_probability", 61),
                "research_confidence": 70,
                "risk_modifier": -4,
                "final_pick": agents.get("prediction_agent", {}).get("pick", "Celtics -4"),
            },
            weights.get("weights"),
        )
        explanation = self.explanation_service.explain(
            {
                "recommended": "PASS" if conflict["conflict"] == "HIGH" else consensus["final_pick"],
                "reason": "Simulation found value. Risk Agent detected volatility. Consensus confidence insufficient.",
            }
        )
        return {
            "messages": self.message_service.history(),
            "debate": debate,
            "conflict": conflict,
            "weights": weights,
            "consensus": consensus,
            "explanation": explanation,
            "reputation": self.reputation_service.score({"accuracy": 59.2}),
        }

    def coordinate_analysis(self, request: dict):
        assignments = self.assign_task(request)
        results = self.collect_results(assignments)
        return {
            "request": request,
            "assignments": assignments,
            "results": results,
        }
