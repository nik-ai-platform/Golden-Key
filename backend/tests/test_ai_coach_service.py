from app.services.ai_coach_service import AICoachService


def test_conversations_save_and_context_is_loaded():
    service = AICoachService()

    result = service.answer_question(7, "Should I bet this?")

    assert result["answer"]
    assert len(service.conversations) == 1
    assert service.conversations[0].user_id == 7
    assert service.conversations[0].message == "Should I bet this?"
    assert service.conversations[0].context["profile"]["risk_level"] in {"MODERATE", "CONSERVATIVE", "AGGRESSIVE", "PROFESSIONAL"}


def test_preferences_influence_response_and_risk_warnings_appear():
    service = AICoachService()

    response = service.answer_question(8, "Why is this my best bet today?")

    assert "risk" in response["answer"].lower()
    assert response["warnings"]
    assert any("uncertainty" in item.lower() or "risk" in item.lower() for item in response["warnings"])


def test_predictions_are_not_modified_and_missing_data_is_safe():
    service = AICoachService()

    predictions = [{"id": 1, "game": "Boston vs Miami", "recommendation": "Boston -3"}]

    result = service.answer_question(9, "Compare my top two bets today")

    assert result["context"]["predictions"]
    assert predictions[0]["recommendation"] == "Boston -3"
    assert result["context"]["predictions"][0]["game"] == "Boston vs Miami"
    assert "missing" in result["answer"].lower() or "available" in result["answer"].lower() or "profile" in result["answer"].lower()
