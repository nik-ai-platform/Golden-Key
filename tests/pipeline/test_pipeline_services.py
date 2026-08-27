from app.services.data_validation_service import DataValidationService
from app.services.feature_pipeline_service import FeaturePipelineService
from app.services.pipeline_monitor_service import PipelineMonitorService
from app.services.prediction_pipeline_service import PredictionPipelineService
from app.services.publishing_service import PublishingService
from app.pipeline.pipeline_context import PipelineContext


def test_data_validation_service_rejects_missing_games():
    service = DataValidationService()
    result = service.validate([], [])
    assert result["valid"] is False
    assert "No games found" in result["errors"]


def test_feature_prediction_and_publishing_services_chain():
    context = PipelineContext(
        games=[{"id": 1, "sport": "NBA", "home_team": "Celtics", "away_team": "Heat"}],
        odds=[{"game_id": 1, "spread": -4.5}],
    )
    feature_service = FeaturePipelineService()
    context.features = feature_service.generate(context.games, context.odds)
    context.npi_scores = [{"game_id": 1, "npi_score": 88.5}]
    context.simulations = [{"summary": {"win_probability": 64.0}}]

    prediction_service = PredictionPipelineService()
    context.predictions = prediction_service.generate(context)
    publish_result = PublishingService().publish(context)

    assert len(context.features) == 1
    assert len(context.predictions) == 1
    assert publish_result["published"] is True


def test_pipeline_monitor_service_metrics_track_success_rate():
    monitor = PipelineMonitorService()
    monitor.start_run("run-1")
    monitor.record_stage("run-1", "Games Imported", True, 11.2, 7)
    monitor.finish_run("run-1", True, [])

    monitor.start_run("run-2")
    monitor.record_stage("run-2", "Games Imported", False, 9.9, 0)
    monitor.finish_run("run-2", False, ["failure"])

    dashboard = monitor.dashboard_metrics()
    assert dashboard["pipeline_status"] in {"completed", "failed"}
    assert dashboard["success_rate"] == 50.0
    assert dashboard["failures"] == 1
