from app.services.v1_read_service import V1ReadService


def _prediction(prediction_id, market, **overrides):
    item = {
        "prediction_id": prediction_id,
        "game_id": prediction_id,
        "sport": "NCAAF",
        "home_team": f"Home {prediction_id}",
        "away_team": f"Away {prediction_id}",
        "game_date": "2026-09-01T20:00:00Z",
        "market": market,
        "selection": "HOME",
        "display_selection": f"Pick {prediction_id}",
        "line_value": -3.5 if market == "spread" else None,
        "american_odds": -110,
        "model_version": "NPI-4.0",
        "npi_score": 170,
        "confidence_score": 80,
        "simulation_probability": 60,
        "projected_edge": 7,
        "risk_level": "LOW",
        "reasoning": None,
        "outcome": None,
    }
    item.update(overrides)
    return item


def test_long_moneyline_is_market_value_not_best_bet():
    service = V1ReadService()
    longshot = _prediction(
        1,
        "moneyline",
        selection="AWAY",
        american_odds=1300,
        npi_score=200,
        confidence_score=95,
        simulation_probability=61,
        projected_edge=54,
    )
    spread = _prediction(2, "spread", npi_score=188, confidence_score=91)

    card = service._build_daily_card([longshot, spread])

    assert card["best_bet"]["prediction"]["prediction_id"] == spread["prediction_id"]
    moneyline = next(
        pick for pick in card["featured_picks"]
        if pick["role"] == "TOP_MONEYLINE"
    )
    assert moneyline["prediction"]["prediction_id"] == longshot["prediction_id"]


def test_daily_card_uses_unique_roles_and_positive_spread_value_play():
    service = V1ReadService()
    predictions = [
        _prediction(1, "spread", npi_score=190),
        _prediction(2, "spread", npi_score=180),
        _prediction(3, "moneyline", american_odds=-135, npi_score=176),
        _prediction(4, "total", selection="OVER", line_value=47.5, npi_score=172),
        _prediction(5, "spread", selection="AWAY", line_value=3.5, npi_score=169),
        _prediction(6, "total", selection="UNDER", line_value=45.5, npi_score=160),
    ]

    card = service._build_daily_card(predictions)
    featured_ids = [
        card["best_bet"]["prediction"]["prediction_id"],
        *[
            pick["prediction"]["prediction_id"]
            for pick in card["featured_picks"]
        ],
    ]

    assert len(featured_ids) == len(set(featured_ids))
    assert [pick["role"] for pick in card["featured_picks"]] == [
        "TOP_SPREAD",
        "TOP_MONEYLINE",
        "TOP_TOTAL",
        "VALUE_PLAY",
    ]
    value_play = card["featured_picks"][-1]["prediction"]
    assert value_play["market"] == "spread"
    assert value_play["line_value"] > 0


def test_daily_card_score_bounds_price_derived_inputs():
    service = V1ReadService()
    prediction = _prediction(
        1,
        "moneyline",
        npi_score=1000,
        confidence_score=500,
        simulation_probability=200,
        projected_edge=500,
    )

    assert service._daily_card_score(prediction) == 100.0


def test_only_long_moneylines_remain_visible_without_a_best_bet():
    service = V1ReadService()
    longshot = _prediction(
        1,
        "moneyline",
        selection="AWAY",
        american_odds=1000,
        npi_score=200,
    )

    card = service._build_daily_card([longshot])

    assert card["best_bet"] is None
    assert card["featured_picks"][0]["role"] == "TOP_MONEYLINE"
    assert card["featured_picks"][0]["prediction"] == longshot