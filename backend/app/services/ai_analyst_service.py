from app.services.analyst_context_service import AnalystContextService


class AIAnalystService:

    def __init__(self, context_service=None):
        self.context_service = context_service or AnalystContextService()

    def generate_analysis(self, game_id):
        context = self.context_service.build_context(game_id)
        return {
            "game_id": game_id,
            "summary": self.explain_prediction(context),
            "risk": self.explain_risk({"risk_score": 42, "risk_level": "LOW"}),
            "context": context,
        }

    def explain_prediction(self, prediction):
        if not prediction:
            return "No prediction available."

        confidence = int(prediction.get("confidence", 0) or 0)
        edge = float(prediction.get("edge", 0.0) or 0.0)
        if confidence >= 80:
            language = "Model strongly favors"
        elif confidence >= 60:
            language = "Model slightly favors"
        else:
            language = "Model sees limited edge"

        return {
            "message": f"{language} {prediction.get('prediction', 'this selection')} with an edge of {edge:.1f}.",
            "language": language,
        }

    def explain_risk(self, risk_data):
        if not risk_data:
            return {"risk_factors": [], "message": "Risk data unavailable."}

        risk_score = int(risk_data.get("risk_score", 0) or 0)
        if risk_score >= 70:
            language = "High risk"
        elif risk_score >= 40:
            language = "Moderate risk"
        else:
            language = "Low risk"

        factors = [
            "Stable lineup",
            "Strong historical matchup",
            "Limited sample size",
            "Market movement against model",
        ]
        return {
            "message": f"{language}: {', '.join(factors[:2])}",
            "risk_score": risk_score,
            "risk_factors": factors,
            "language": language,
        }

    def answer_question(self, question, context):
        if not question:
            return {"answer": "No question provided."}

        if not context:
            return {"answer": "No context available for this question."}

        return {
            "answer": f"The model favors {context.get('prediction', 'this selection')} because the available context indicates a positive edge and manageable risk.",
        }
