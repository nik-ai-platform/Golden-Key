from typing import Dict


class AIAnalysisEngine:

    VERSION = "AI-1.0"

    def generate_analysis(
        self,
        prediction_data: Dict
    ):

        factors = prediction_data.get(
            "factors",
            []
        )

        strengths = []
        risks = []

        for factor in factors:

            score = factor.get(
                "score",
                0
            )

            weight = factor.get(
                "weight",
                0
            )

            if score >= weight * 0.75:

                strengths.append(
                    factor.get("explanation")
                )

            elif score <= weight * 0.35:

                risks.append(
                    factor.get("explanation")
                )

        confidence = prediction_data.get(
            "confidence_score",
            0
        )

        recommendation = self.generate_summary(
            confidence
        )

        return {

            "engine_version":
                self.VERSION,

            "summary":
                recommendation,

            "strengths":
                strengths,

            "risks":
                risks,

            "confidence":
                confidence,

            "explanation":
                self.build_explanation(
                    prediction_data,
                    strengths,
                    risks
                )
        }

    def generate_summary(
        self,
        confidence
    ):

        if confidence >= 80:
            return (
                "Strong Golden Key edge detected."
            )

        if confidence >= 70:
            return (
                "Positive value opportunity identified."
            )

        if confidence >= 55:
            return (
                "Moderate edge. Monitor risk."
            )

        return (
            "Insufficient advantage. Avoid."
        )

    def build_explanation(
        self,
        data,
        strengths,
        risks
    ):

        explanation = []

        explanation.append(
            f"NPI Score: "
            f"{data.get('npi_score')}/200"
        )

        explanation.append(
            f"Simulation Probability: "
            f"{data.get('simulation_probability')}%"
        )

        if strengths:

            explanation.append(
                "Key Advantages: "
                +
                ", ".join(strengths)
            )

        if risks:

            explanation.append(
                "Risk Factors: "
                +
                ", ".join(risks)
            )

        return " ".join(
            explanation
        )
