from types import SimpleNamespace

from app.services.nik_power_engine import NikPowerEngine


def _performance(
    wins,
    losses,
    offensive_rating,
    defensive_rating,
    recent_form,
):
    return SimpleNamespace(
        wins=wins,
        losses=losses,
        offensive_rating=offensive_rating,
        defensive_rating=defensive_rating,
        recent_form=recent_form,
    )


def _analytics(
    implied_home_probability,
    implied_away_probability,
    home_rest_days,
    away_rest_days,
    home_back_to_back,
    away_back_to_back,
    favorite_is_home,
):
    return SimpleNamespace(
        implied_home_probability=implied_home_probability,
        implied_away_probability=implied_away_probability,
        home_rest_days=home_rest_days,
        away_rest_days=away_rest_days,
        home_back_to_back=home_back_to_back,
        away_back_to_back=away_back_to_back,
        favorite_is_home=favorite_is_home,
    )


def test_calculate_team_score_uses_40_20_20_10_10_weights_for_home():
    engine = NikPowerEngine()

    performance = _performance(
        wins=8,
        losses=2,
        offensive_rating=90,
        defensive_rating=50,
        recent_form=70,
    )

    analytics = _analytics(
        implied_home_probability=0.60,
        implied_away_probability=0.40,
        home_rest_days=2,
        away_rest_days=0,
        home_back_to_back=False,
        away_back_to_back=True,
        favorite_is_home=True,
    )

    # Components:
    # strength=80, recent_form=70, offense/defense=70, market=60, situational=90
    expected = 75.00

    result = engine.calculate_team_score(
        performance,
        analytics,
        is_home=True,
    )

    assert result["score"] == expected

    assert result["components"] == {
        "strength": 80.0,
        "form": 70,
        "offense_defense": 70.0,
        "market": 60.0,
        "situational": 90.0,
    }


def test_calculate_team_score_applies_away_market_and_situational_context():
    engine = NikPowerEngine()

    performance = _performance(
        wins=8,
        losses=2,
        offensive_rating=90,
        defensive_rating=50,
        recent_form=70,
    )

    analytics = _analytics(
        implied_home_probability=0.60,
        implied_away_probability=0.40,
        home_rest_days=2,
        away_rest_days=0,
        home_back_to_back=False,
        away_back_to_back=True,
        favorite_is_home=True,
    )

    # Away components:
    # strength=80, recent_form=70, offense/defense=70, market=40, situational=16.67
    expected = 65.67

    result = engine.calculate_team_score(
        performance,
        analytics,
        is_home=False,
    )

    assert result["score"] == expected

    assert result["components"] == {
        "strength": 80.0,
        "form": 70,
        "offense_defense": 70.0,
        "market": 40.0,
        "situational": 16.67,
    }


def test_calculate_team_score_returns_default_for_missing_performance():
    engine = NikPowerEngine()

    result = engine.calculate_team_score(
        performance=None,
        analytics=None,
        is_home=True,
    )

    assert result == {
        "score": 50,
        "components": {
            "strength": 50,
            "form": 50,
            "offense_defense": 50,
            "market": 50,
            "situational": 50,
        },
    }
