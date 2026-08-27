from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_intelligence_module():
    module_path = Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "intelligence.py"
    spec = spec_from_file_location("intelligence_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyze_endpoint_returns_integrated_intelligence():
    module = _load_intelligence_module()
    data = module.analyze({"question": "Why is this team undervalued?", "context": {"season_stage": "playoffs"}})

    assert "analysis" in data
    assert "persona" in data
    assert "context" in data


def test_explain_endpoint_returns_reasoning_payload():
    module = _load_intelligence_module()
    data = module.explain({"question": "Why does Golden Key like this matchup?", "matchup": "Chiefs vs Bills"})

    assert "explanation" in data
    assert "analysis" in data


def test_research_compare_and_strategy_endpoints_return_expected_shapes():
    module = _load_intelligence_module()

    research = module.research()
    compare = module.compare({"team_a": "Chiefs", "team_b": "Bills"})
    strategy = module.strategy({"objective": "Improve NBA totals model"})

    assert "plan" in research
    assert "matchup" in compare
    assert "actions" in strategy
