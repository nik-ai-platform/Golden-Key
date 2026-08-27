from app.services.npi_engine import NPIEngine


def make_odds(spread_home=-4.5, total=48):
    return type(
        "Odds",
        (),
        {
            "spread_home": spread_home,
            "total": total,
        },
    )()


def test_npi_score_range():
    result = NPIEngine().calculate(
        game=None,
        odds=make_odds(),
    )

    assert 0 <= result["npi_score"] <= 200


def test_npi_weights_total_200():
    engine = NPIEngine()

    assert sum(engine.weights.values()) == 200


def test_every_factor_stays_within_its_weight():
    result = NPIEngine().calculate(
        game=None,
        odds=make_odds(spread_home=-5.5, total=50),
    )

    for factor in result["factors"]:
        assert 0 <= factor["score"] <= factor["weight"]


def test_historical_rule_contributes_to_80_point_bucket():
    result = NPIEngine().calculate(
        game=None,
        odds=make_odds(spread_home=-5.5),
    )

    historical = next(
        factor
        for factor in result["factors"]
        if factor["name"] == "Historical Rule Engine"
    )

    assert historical["weight"] == 80
    assert historical["score"] == 28


def test_npi_supports_custom_weights_when_total_is_200():
    weights = {
        "Home Advantage": 20,
        "Spread Value": 30,
        "Market Environment": 20,
        "Situational Edge": 30,
        "Historical Rule Engine": 100,
    }

    result = NPIEngine(weights=weights).calculate(
        game=None,
        odds=make_odds(),
    )

    assert result["max_score"] == 200
    assert sum(
        factor["weight"]
        for factor in result["factors"]
    ) == 200


def test_npi_uses_database_profile_when_session_is_supplied(monkeypatch):
    profile = {
        "home_advantage": 10,
        "spread_value": 20,
        "market_environment": 30,
        "situational_edge": 40,
        "historical_rules": 100,
    }
    calls = []

    def get_profile(db, sport, model_version):
        calls.append((db, sport, model_version))
        return profile

    monkeypatch.setattr(
        NPIEngine.weight_profiles,
        "get_profile",
        get_profile,
    )
    database_session = object()

    result = NPIEngine().calculate(
        db=database_session,
        game=None,
        odds=make_odds(),
        sport="NBA",
        model_version="v3",
    )

    assert calls == [(database_session, "NBA", "v3")]
    assert [
        factor["weight"]
        for factor in result["factors"]
    ] == list(profile.values())
