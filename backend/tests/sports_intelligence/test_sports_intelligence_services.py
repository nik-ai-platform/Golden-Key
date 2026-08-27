from app.services.ai_persona_service import AIPersonaService
from app.services.context_awareness_service import ContextAwarenessService
from app.services.cross_sport_learning_service import CrossSportLearningService
from app.services.sports_intelligence_core_service import SportsIntelligenceCoreService
from app.services.sports_reasoning_service import SportsReasoningService
from app.services.universal_matchup_service import UniversalMatchupService


def test_knowledge_retrieval_and_matchup_analysis():
    service = UniversalMatchupService()
    result = service.analyze_matchup({"team_a": "Chiefs", "team_b": "Bills"})

    assert result["team_a"] == "Chiefs"
    assert "strength" in result


def test_cross_sport_reasoning_transfers_patterns():
    service = CrossSportLearningService()
    transfer = service.transfer_patterns()
    comparison = service.compare_sports("NFL", "NBA")

    assert transfer["patterns"]["NFL"] == "Rest disadvantage"
    assert comparison["shared_factor"] == "fatigue management"


def test_model_integration_core_combine_and_analyze():
    core = SportsIntelligenceCoreService()
    result = core.analyze("Why is this team undervalued?")

    assert result["conclusion"] == "Potential value opportunity"
    assert result["reasoning"]


def test_explanation_quality_contains_three_reasons():
    service = SportsReasoningService()
    explanation = service.explain({"matchup": "this matchup"})

    assert "1." in explanation["explanation"]
    assert "2." in explanation["explanation"]
    assert "3." in explanation["explanation"]


def test_context_awareness_detects_stage_pressure_and_intensity():
    service = ContextAwarenessService()
    regular = service.assess({"season_stage": "regular"})
    playoffs = service.assess({"season_stage": "playoffs"})

    assert regular["intensity"] == "lower"
    assert playoffs["playoff_pressure"] == "high"


def test_memory_and_persona_retention_like_behavior():
    personas = AIPersonaService().get_personas()
    assignment = AIPersonaService().assign_for_question("How is market value shifting?")

    assert len(personas) == 4
    assert assignment["persona"]["name"] == "The Trader"
