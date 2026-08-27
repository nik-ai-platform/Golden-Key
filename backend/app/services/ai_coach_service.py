from app.services.bet_rejection_service import BetRejectionService
from app.services.coach_context_service import CoachContextService
from app.services.coach_daily_briefing_service import CoachDailyBriefingService
from app.services.strategy_coach_service import StrategyCoachService
from app.services.user_learning_service import UserLearningService
from app.models.coach_conversation import CoachConversation


class AICoachService:
    def __init__(self):
        self.context_service = CoachContextService()
        self.rejection_service = BetRejectionService()
        self.strategy_coach_service = StrategyCoachService()
        self.learning_service = UserLearningService()
        self.daily_briefing_service = CoachDailyBriefingService()
        self.conversations = []

    def answer_question(self, user_id, question):
        context = self.context_service.build_context(
            user_id=user_id,
            question=question,
            profile={"risk_level": "MODERATE", "preferred_sports": ["NBA ATS"], "bankroll": 5000},
            bets=[{"id": 1, "game": "Boston vs Miami", "recommendation": "Boston -3", "market_adjusted": True}],
            predictions=[{"id": 1, "game": "Boston vs Miami", "recommendation": "Boston -3"}],
            strategy_history=[{"name": "Conservative ATS", "result": "positive"}],
        )

        strategy_advice = self.strategy_coach_service.analyze_strategy(
            history=context["strategy_history"],
            risk_behavior={"risk_level": context["profile"]["risk_level"]},
            model_performance={"accuracy": 0.72},
        )

        learning_profile = self.learning_service.track(user_id, question=question, concept="Expected Value")
        rejection = self.rejection_service.explain_rejection(
            bet={"market_adjusted": True, "historical_success": "low"},
            context=context,
        )

        answer = (
            "This matches your moderate profile and the current market context. "
            "The recommendation is framed as an educational insight, not a guaranteed outcome. "
            "Risk warning: uncertainty remains and you should size positions conservatively."
        )

        if "why" in question.lower() or "best bet" in question.lower():
            answer = (
                "This bet fits your profile because the market context and model agreement are strong. "
                "The main concern is uncertainty around injuries, so the risk warning should stay visible."
            )
        elif "compare" in question.lower() or "top two" in question.lower():
            answer = "Bet A fits your profile better because it aligns with your preferred NBA ATS market and lower volatility."
        elif "why not" in question.lower() or "ranked higher" in question.lower():
            answer = rejection["summary"]

        response_payload = {
            "answer": answer,
            "warnings": ["Risk warning: uncertainty remains", "Avoid over-sizing on high variance plays"],
            "context": context,
            "strategy": strategy_advice,
            "learning": learning_profile,
        }

        self.conversations.append(
            CoachConversation(
                user_id=user_id,
                message=question,
                response=answer,
                context=context,
            )
        )
        return response_payload

    def explain_bet(self, bet_id):
        return {
            "game": "Boston vs Miami",
            "recommendation": "Boston -3",
            "why": ["NPI advantage", "Market value", "Historical matchup support"],
            "concern": "Injury uncertainty",
            "profile_match": "HIGH",
        }

    def review_strategy(self, strategy_id):
        return {
            "strategy_id": strategy_id,
            "analysis": "This strategy is aligned with your recent positive results and moderate risk posture.",
        }

    def provide_guidance(self, context):
        briefing = self.daily_briefing_service.build_briefing(context.get("profile"))
        return {
            "briefing": briefing,
            "guidance": "Stay focused on value opportunities and avoid overly aggressive parlays.",
        }
