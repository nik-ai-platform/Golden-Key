import importlib


def test_conversations_save():
    service = importlib.import_module("app.services.ai_assistant_service").AIAssistantService()
    result = service.process_message(user=type("User", (), {"id": 1, "profile": {"risk_level": "Moderate", "bankroll": 5000, "favorite_team": "Atlanta Hawks", "favorite_sports": ["NBA", "NCAAB"], "betting_style": "underdog value"}})(), message="Best NBA picks tonight")
    assert result["answer"]
    assert result["conversation_id"] is not None


def test_memory_retrieval_works():
    service = importlib.import_module("app.services.ai_assistant_service").AIAssistantService()
    service.process_message(user=type("User", (), {"id": 1, "profile": {"risk_level": "Moderate", "bankroll": 5000, "favorite_team": "Atlanta Hawks", "favorite_sports": ["NBA", "NCAAB"], "betting_style": "underdog value"}})(), message="Am I risking too much?")
    memory = service.memory_service.get_memory()
    assert memory["preferences"]


def test_context_loads():
    context_service = importlib.import_module("app.services.ai_context_service").AIContextService()
    context = context_service.build_context(user=type("User", (), {"id": 1, "profile": {"risk_level": "Moderate", "bankroll": 5000, "favorite_team": "Atlanta Hawks", "favorite_sports": ["NBA", "NCAAB"], "betting_style": "underdog value"}})(), message="Should I take this?")
    assert context["risk_profile"] == "Moderate"


def test_ai_routing_works():
    router = importlib.import_module("app.services.query_router_service").QueryRouterService()
    assert router.route("Best NBA picks tonight") == "Prediction Service"
    assert router.route("Am I risking too much?") == "Portfolio Risk Service"


def test_explanations_match_data():
    service = importlib.import_module("app.services.prediction_explanation_service").PredictionExplanationService()
    explanation = service.generate_explanation(home_components={"strength": 78, "form": 82, "offense_defense": 91}, away_components={"strength": 72, "form": 74, "offense_defense": 85}, recommendation="Boston -4.5")
    assert "recommendation" in explanation
    assert explanation["reasons"]


def test_guardrails_trigger():
    service = importlib.import_module("app.services.ai_guardrail_service").AIGuardrailService()
    guarded = service.apply_guardrails("This will win.")
    assert "guarantee" in guarded.lower() or "responsible" in guarded.lower()


def test_permissions_enforced():
    service = importlib.import_module("app.services.ai_assistant_service").AIAssistantService()
    result = service.process_message(user=type("User", (), {"id": 1, "profile": {"risk_level": "Moderate", "bankroll": 5000, "favorite_team": "Atlanta Hawks", "favorite_sports": ["NBA", "NCAAB"], "betting_style": "underdog value"}})(), message="Review my portfolio")
    assert result["answer"]
