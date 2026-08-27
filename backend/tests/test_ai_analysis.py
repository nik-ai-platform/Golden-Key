from app.services.ai_analysis_engine import (
    AIAnalysisEngine
)


def test_ai_explanation():

    engine = AIAnalysisEngine()

    result = engine.generate_analysis(
        {
            "npi_score": 160,

            "simulation_probability": 68,

            "confidence_score": 82,

            "factors": [
                {
                    "score": 20,
                    "weight": 20,
                    "explanation":
                    "Strong market value"
                }
            ]
        }
    )

    assert (
        "Strong"
        in result["summary"]
    )
