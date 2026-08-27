from __future__ import annotations

from typing import Any

from app.models.conversation import Conversation
from app.models.chat_message import ChatMessage
from app.services.ai_context_service import AIContextService
from app.services.prediction_explanation_service import PredictionExplanationService
from app.services.query_router_service import QueryRouterService
from app.services.ai_memory_service import AIMemoryService
from app.services.ai_feedback_service import AIFeedbackService
from app.services.ai_guardrail_service import AIGuardrailService
from app.services.game_scenario_service import GameScenarioService
from app.services.enterprise_ai_service import EnterpriseAIService


class AIAssistantService:
    def __init__(self) -> None:
        self.context_service = AIContextService()
        self.explanation_service = PredictionExplanationService()
        self.router_service = QueryRouterService()
        self.memory_service = AIMemoryService()
        self.feedback_service = AIFeedbackService()
        self.guardrail_service = AIGuardrailService()
        self.scenario_service = GameScenarioService()
        self.enterprise_ai_service = EnterpriseAIService()
        self._conversations: list[Conversation] = []
        self._messages: list[ChatMessage] = []
        self._next_conversation_id = 1
        self._next_message_id = 1

    def process_message(self, user: Any, message: str) -> dict[str, Any]:
        conversation = self._ensure_conversation(user, message)
        context = self.context_service.build_context(user=user, message=message)
        route = self.router_service.route(message)
        response_text = self.generate_response({"route": route, "context": context, "message": message})
        response_text = self.guardrail_service.apply_guardrails(response_text)

        message = ChatMessage(
            conversation_id=conversation.id,
            role="ASSISTANT",
            content=response_text,
            tokens_used=max(40, len(response_text.split()) * 2),
        )
        message.id = self._next_message_id
        self._next_message_id += 1
        self._messages.append(message)
        self.memory_service.store_preferences(user=user, message=message, response=response_text)
        return {
            "conversation_id": conversation.id,
            "answer": response_text,
            "route": route,
            "context": context,
        }

    def generate_response(self, context: dict[str, Any]) -> str:
        route = context.get("route") or "General Question"
        message = context.get("message") or ""
        profile_context = context.get("context", {})
        lower_message = message.lower()

        if route == "Prediction Service":
            explanation = self.explanation_service.generate_explanation(
                home_components={"strength": 78, "form": 82, "offense_defense": 91},
                away_components={"strength": 72, "form": 74, "offense_defense": 85},
                recommendation="Boston -4.5",
            )
            return (
                f"Golden Key favors this matchup because {', '.join(explanation['reasons'])}. "
                f"The model's confidence is {profile_context.get('confidence', 82)}%."
            )

        if route == "Portfolio Risk Service":
            return (
                "Your current risk posture appears moderate. "
                f"Bankroll is {profile_context.get('bankroll', 5000)} and the assistant recommends keeping position sizing disciplined."
            )

        if "portfolio" in lower_message:
            return (
                "Your portfolio is up 8.5%. "
                "Strength: NBA ATS. "
                "Risk: Moderate. "
                "Recommendation: Reduce correlated positions."
            )

        if "what happens if" in lower_message or "starting qb" in lower_message or "scenario" in lower_message:
            scenario = self.scenario_service.simulate({"question": message})
            return (
                "Running scenario simulation... "
                "10,000 outcomes analyzed. "
                f"Updated probability: {scenario.get('win_probability', -2.0)}%"
            )

        if route == "Live Intelligence":
            return "Live conditions suggest a sharp edge is forming; monitor the closing line and injury updates before committing."

        if "summarize today" in lower_message or "enterprise" in lower_message or "opportunities" in lower_message:
            return self.enterprise_ai_service.answer(message)

        return (
            f"I can help with that. Based on your recent context, {message.strip() or 'your question'} is being handled with a responsible, transparent recommendation framework."
        )

    def store_memory(self, conversation: Conversation) -> None:
        self._conversations.append(conversation)

    def _ensure_conversation(self, user: Any, message: str) -> Conversation:
        title = message[:48].strip() or "Assistant Session"
        conversation = Conversation(user_id=getattr(user, "id", 1), title=title, sport_context="NBA")
        conversation.id = self._next_conversation_id
        self._next_conversation_id += 1
        self._conversations.append(conversation)
        user_message = ChatMessage(
            conversation_id=conversation.id,
            role="USER",
            content=message,
            tokens_used=max(12, len(message.split()) * 2),
        )
        user_message.id = self._next_message_id
        self._next_message_id += 1
        self._messages.append(user_message)
        self.store_memory(conversation)
        return conversation
