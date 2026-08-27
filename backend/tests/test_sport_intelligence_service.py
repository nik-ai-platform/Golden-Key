from app.services.cross_sport_analysis_service import CrossSportAnalysisService
from app.services.cross_sport_learning_service import CrossSportLearningService
from app.services.league_comparison_service import LeagueComparisonService
from app.services.sport_intelligence_service import SportIntelligenceService
from app.services.sport_weight_service import SportWeightService
from app.services.universal_feature_service import UniversalFeatureService


def test_sports_remain_isolated_and_weights_stay_sport_specific():
    service = SportIntelligenceService()
    assert service.get_model("NBA")["model"] == "NPI-NBA-v5.4"
    assert service.get_features("NFL")["features"] == ["matchup", "weather", "injury"]

    weight_service = SportWeightService()
    nba_weights = weight_service.get_weights("NBA")
    nfl_weights = weight_service.get_weights("NFL")
    assert nba_weights["weights"]["pace"] > nfl_weights["weights"].get("pace", 0)


def test_features_transfer_safely_and_cross_sport_analysis_is_accurate():
    universal_service = UniversalFeatureService()
    feature = universal_service.track_feature("Rest Advantage", "NBA", True)
    assert feature["is_universal"] is True

    learning = CrossSportLearningService().learn("Pace", "NFL", False)
    assert learning["status"] == "rejected"

    analysis = CrossSportAnalysisService().analyze("Rest Advantage", "NBA", "+2.4% ROI", "strong", "+2.4% ROI")
    assert analysis["recommendation"] == "Prioritize NBA usage"

    comparison = LeagueComparisonService().compare([])
    assert comparison["summary"][0]["sport"] == "NBA"
