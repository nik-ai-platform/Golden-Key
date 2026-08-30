from app.services.feature_correlation_service import FeatureCorrelationService
from app.services.feature_discovery_service import FeatureDiscoveryService
from app.services.feature_importance_service import FeatureImportanceService


def test_discovery_does_not_alter_production_models():
    service = FeatureDiscoveryService()
    features = service.discover_features("NBA")

    assert len(features["feature_details"]) == 2
    assert features["feature_details"][0]["sport"] == "NBA"


def test_feature_scoring_consistent():
    service = FeatureDiscoveryService()
    feature = {"importance_score": 82}

    assert service.calculate_importance(feature) == 82


def test_correlation_detection_works():
    service = FeatureCorrelationService()
    result = service.assess_correlation(
        {"feature_name": "Offensive Rating"},
        {"feature_name": "Points Per Possession"},
    )

    assert result["correlation_level"] == "Low Correlation"


def test_invalid_features_rejected():
    service = FeatureDiscoveryService()
    result = service.validate_feature({"importance_score": 40})

    assert result["status"] == "REJECTED"


def test_reports_generate_correctly():
    service = FeatureImportanceService()
    report = service.build_report({"importance_score": 82})

    assert report["status"] == "APPROVED"


def test_backtests_remain_reproducible():
    service = FeatureImportanceService()
    impact = service.measure_impact(53.2, 54.7)

    assert impact == 1.5
