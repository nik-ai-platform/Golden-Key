from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from app.core.golden_key_engine import GoldenKeyEngine
from app.services.daily_pipeline_service import DailyPipelineService
from app.services.system_health_service import SystemHealthService


def _load_intelligence_module():
    module_path = Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "intelligence.py"
    spec = spec_from_file_location("intelligence_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daily_pipeline_chain_from_import_to_dashboard_publish():
    pipeline = DailyPipelineService()
    result = pipeline.run_daily_workflow("06:00")

    assert result["published"] is True
    assert "Import Games" in result["stages"]
    assert "Import Odds" in result["stages"]
    assert "Calculate NPI" in result["stages"]
    assert "Run Models" in result["stages"]
    assert "Run Simulation" in result["stages"]
    assert "AI Analysis" in result["stages"]
    assert "Generate Picks" in result["stages"]
    assert "Publish Dashboard" in result["stages"]
    assert len(result["picks"]) > 0


def test_engine_prediction_simulation_and_ai_explanation_flow():
    engine = GoldenKeyEngine()
    analysis = engine.analyze_game(101)
    report = engine.create_report(analysis)

    assert analysis["prediction"]["pick"]
    assert analysis["prediction"]["npi_score"] > 0
    assert "ai" in analysis["intelligence"]
    assert "reason" in analysis["intelligence"]["ai"]
    assert "summary" in report


def test_intelligence_api_shapes_today_game_top_picks_and_reports():
    module = _load_intelligence_module()

    today = module.today_intelligence()
    game = module.game_intelligence(101)
    top = module.top_picks()
    reports = module.intelligence_reports()

    assert "top_pick" in today
    assert "confidence" in today
    assert "prediction" in game
    assert "picks" in top
    assert "reports" in reports


def test_system_health_payload_contains_required_services():
    health = SystemHealthService().check()

    assert "database" in health
    assert "models" in health
    assert "pipeline" in health
    assert "workers" in health
