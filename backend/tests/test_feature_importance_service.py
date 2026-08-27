from types import SimpleNamespace

from app.services.feature_importance_service import FeatureImportanceService


def test_feature_contributions_are_deterministic():
    service = FeatureImportanceService()
    features = {
        "momentum": 84,
        "strength": 77,
        "offense": 73,
        "defense": 61,
        "rest_days": 58,
        "market_odds": 64,
        "recent_form": 79,
    }

    first = [item.model_dump() for item in service.calculate_feature_scores(features)]
    second = [item.model_dump() for item in service.calculate_feature_scores(features)]

    assert first == second


def test_rank_features_orders_by_absolute_contribution():
    service = FeatureImportanceService()
    contributions = service.calculate_feature_scores(
        {
            "momentum": 95,
            "strength": 55,
            "offense": 52,
            "defense": 85,
            "rest_days": 50,
            "market_odds": 54,
            "recent_form": 51,
        }
    )

    ranked = service.rank_features(contributions)

    assert ranked[0].feature in {"Defensive Rating", "Momentum"}
    assert abs(ranked[0].contribution) >= abs(ranked[1].contribution)
    assert abs(ranked[1].contribution) >= abs(ranked[2].contribution)


def test_missing_feature_values_are_handled_gracefully():
    service = FeatureImportanceService()

    contributions = service.calculate_feature_scores(
        {
            "momentum": 90,
            "recent_form": 75,
        }
    )

    as_map = {item.feature: item for item in contributions}

    assert as_map["Momentum"].contribution > 0
    assert as_map["Recent Form"].contribution > 0
    assert as_map["Rest Days"].contribution == 0.0
    assert as_map["Market Odds"].contribution == -0.0


def test_explanation_returns_expected_positive_and_negative_factors():
    service = FeatureImportanceService()
    prediction = SimpleNamespace(
        id=1421,
        recommendation="Boston Celtics",
        confidence=87.4,
    )

    explanation = service.explain_prediction(
        prediction,
        features={
            "momentum": 92,
            "strength": 85,
            "offense": 79,
            "defense": 68,
            "rest_days": 48,
            "market_odds": 72,
            "recent_form": 88,
        },
    )

    assert explanation.prediction_id == 1421
    assert explanation.winner == "Boston Celtics"
    assert explanation.confidence == 87.4
    assert len(explanation.top_positive) > 0
    assert len(explanation.top_negative) > 0
    assert explanation.top_positive[0].feature == "Momentum"
    assert explanation.top_negative[0].feature == "Market Odds"


def test_historical_importance_produces_stable_aggregation():
    service = FeatureImportanceService()

    snapshots = [
        SimpleNamespace(
            home_score=110,
            away_score=99,
            home_features={
                "momentum": 90,
                "strength": 78,
                "offense": 80,
                "defense": 60,
                "rest_days": 56,
                "market_odds": 65,
                "recent_form": 82,
            },
            away_features={},
        ),
        SimpleNamespace(
            home_score=101,
            away_score=108,
            home_features={},
            away_features={
                "momentum": 88,
                "strength": 76,
                "offense": 79,
                "defense": 62,
                "rest_days": 54,
                "market_odds": 63,
                "recent_form": 80,
            },
        ),
    ]

    class _Query:
        def all(self):
            return snapshots

    class _FakeDB:
        def query(self, _model):
            return _Query()

    result = service.historical_importance(_FakeDB())

    assert len(result) == 7
    assert result[0]["feature"] == "Momentum"
    assert result[0]["average_contribution"] > 0