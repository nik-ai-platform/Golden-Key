from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.main import app
from app.models.game import Game
from app.models.model_registry import ModelRegistry
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.services.parlay_optimizer_service import (
    ParlayOptimizationError,
    ParlayOptimizerService,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [
            ModelRegistry(
                model_name=f"{sport} production model",
                model_version="NPI-4.0",
                sport=sport,
                version="4.0",
                is_active=True,
                production_status=True,
            )
            for sport in ("NFL", "NCAAF")
        ]
    )
    db.commit()
    return db


def _add_candidate(
    db,
    index,
    market,
    *,
    selection=None,
    stale=False,
    edge=6.0,
    american_odds=None,
):
    home = Team(name=f"Home {index}", sport="NFL", league="NFL")
    away = Team(name=f"Away {index}", sport="NFL", league="NFL")
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport="NFL",
        league="NFL",
        season=2026,
        provider_game_id=f"parlay-game-{index}",
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
    )
    db.add(game)
    db.flush()
    observed_at = datetime.now(UTC).replace(tzinfo=None) - (
        timedelta(hours=8) if stale else timedelta(minutes=index)
    )
    if selection is None:
        selection = (
            "OVER" if index % 2 else "UNDER"
        ) if market == "total" else "HOME"
    odds = Odds(
        game_id=game.id,
        sportsbook="Test Book",
        spread_home=-3.5,
        spread_away=3.5,
        spread_home_price=-110,
        spread_away_price=-110,
        moneyline_home=(
            american_odds
            if market == "moneyline" and selection == "HOME" and american_odds is not None
            else -150
        ),
        moneyline_away=(
            american_odds
            if market == "moneyline" and selection == "AWAY" and american_odds is not None
            else 130
        ),
        total=44.5,
        total_over_price=-110,
        total_under_price=-110,
        created_at=observed_at,
    )
    db.add(odds)
    db.flush()
    prediction = Prediction(
        game_id=game.id,
        model_version="NPI-4.0",
        market=market,
        selection=selection,
        line_value=None if market == "moneyline" else (
            (3.5 if selection == "AWAY" else -3.5) if market == "spread" else 44.5
        ),
        american_odds=(
            american_odds
            if american_odds is not None
            else (
                odds.moneyline_home
                if market == "moneyline" and selection == "HOME"
                else odds.moneyline_away
                if market == "moneyline"
                else -110
            )
        ),
        odds_snapshot_id=odds.id,
        sportsbook=odds.sportsbook,
        odds_observed_at=observed_at,
        npi_score=170 - index,
        simulation_probability=72,
        confidence_score=82,
        projected_edge=-edge if selection in {"AWAY", "UNDER"} and market != "moneyline" else edge,
        risk_level="LOW" if index % 3 else "HIGH",
        reasoning=f"Qualified because model signals agree for candidate {index}.",
    )
    db.add(prediction)
    db.commit()
    return game, prediction


@pytest.mark.parametrize(
    ("leg_count", "moneyline_max", "spread_min", "total_min"),
    [(2, 1, 0, 0), (4, 2, 1, 1), (6, 2, 2, 1), (8, 3, 2, 2), (10, 3, 3, 2)],
)
def test_optimizer_builds_every_supported_parlay_when_inventory_is_sufficient(
    leg_count,
    moneyline_max,
    spread_min,
    total_min,
):
    db = _session()
    markets = ["moneyline"] * 5 + ["spread"] * 5 + ["total"] * 5
    for index, market in enumerate(markets, start=1):
        _add_candidate(db, index, market)

    result = ParlayOptimizerService().build_parlay(db, leg_count=leg_count)

    assert len(result["legs"]) == leg_count
    assert len({leg["game_id"] for leg in result["legs"]}) == leg_count
    assert result["market_mix"]["moneyline"] <= moneyline_max
    assert result["market_mix"]["spread"] >= spread_min
    assert result["market_mix"]["total"] >= total_min
    assert all("parlay_score" not in leg and "score_components" not in leg for leg in result["legs"])
    assert all(leg["reasoning"] for leg in result["legs"])


def test_optimizer_excludes_stale_pass_missing_provenance_and_low_edge():
    db = _session()
    _, qualified = _add_candidate(db, 1, "spread")
    _add_candidate(db, 2, "moneyline")
    _add_candidate(db, 3, "total", stale=True)
    _, passed = _add_candidate(db, 4, "spread", selection="PASS")
    _, low_edge = _add_candidate(db, 5, "total", edge=0.5)
    _, missing = _add_candidate(db, 6, "moneyline")
    missing.odds_snapshot_id = None
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)
    selected_ids = {leg["prediction_id"] for leg in result["legs"]}

    assert qualified.id in selected_ids
    assert passed.id not in selected_ids
    assert low_edge.id not in selected_ids
    assert missing.id not in selected_ids


def test_optimizer_never_selects_two_markets_from_the_same_game():
    db = _session()
    game, first = _add_candidate(db, 1, "spread")
    odds = db.get(Odds, first.odds_snapshot_id)
    db.add(
        Prediction(
            game_id=game.id,
            model_version="NPI-4.0",
            market="moneyline",
            selection="HOME",
            american_odds=-150,
            odds_snapshot_id=odds.id,
            sportsbook=odds.sportsbook,
            odds_observed_at=odds.created_at,
            npi_score=199,
            simulation_probability=90,
            confidence_score=95,
            projected_edge=9,
            risk_level="LOW",
            reasoning="Correlated same-game candidate.",
        )
    )
    _add_candidate(db, 2, "total", selection="UNDER")
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)

    assert len({leg["game_id"] for leg in result["legs"]}) == 2
    assert len({leg["prediction_id"] for leg in result["legs"]}) == 2


def test_optimizer_uses_the_selected_sportsbook_quote_instead_of_standard_price():
    db = _session()
    _, spread = _add_candidate(db, 1, "spread")
    _, total = _add_candidate(db, 2, "total", selection="UNDER")
    spread_snapshot = db.get(Odds, spread.odds_snapshot_id)
    total_snapshot = db.get(Odds, total.odds_snapshot_id)
    spread_snapshot.spread_home_price = -108
    total_snapshot.total_under_price = 102
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)
    selected = {leg["prediction_id"]: leg for leg in result["legs"]}

    assert selected[spread.id]["american_odds"] == -108
    assert selected[spread.id]["sportsbook"] == spread.sportsbook
    assert selected[total.id]["american_odds"] == 102
    assert selected[total.id]["sportsbook"] == total.sportsbook


def test_optimizer_offers_best_smaller_valid_parlay_when_requested_inventory_is_short():
    db = _session()
    for index, market in enumerate(("spread", "total", "moneyline", "spread"), start=1):
        _add_candidate(db, index, market)

    result = ParlayOptimizerService().build_parlay(db, leg_count=6)

    assert result["requested_leg_count"] == 6
    assert result["leg_count"] == 4
    assert len(result["legs"]) == 4
    assert len({leg["game_id"] for leg in result["legs"]}) == 4
    assert result["adjustment_reason"]


def test_optimizer_reports_specific_reason_when_fewer_than_two_games_qualify():
    db = _session()
    _add_candidate(db, 1, "spread")

    with pytest.raises(
        ParlayOptimizationError,
        match="Only 1 distinct game has a valid quoted pick",
    ):
        ParlayOptimizerService().build_parlay(db, leg_count=6)


def test_optimizer_preserves_prediction_game_snapshot_and_selected_price_identity():
    db = _session()
    fixtures = [
        ("Nebraska", "Cincinnati", "moneyline", "HOME", None, -201),
        ("Clemson", "Duke", "moneyline", "AWAY", None, 182),
        ("Army", "Tarleton State", "total", "OVER", 43.0, -110),
        ("Ohio", "Rutgers", "spread", "HOME", -7.5, -110),
    ]
    predictions = []
    expected_games = {}
    now = datetime.now(UTC).replace(tzinfo=None)

    for index, (home_name, away_name, market, selection, line, price) in enumerate(
        fixtures,
        start=1,
    ):
        home = Team(name=home_name, sport="NCAAF", league="NCAAF")
        away = Team(name=away_name, sport="NCAAF", league="NCAAF")
        db.add_all([home, away])
        db.flush()
        game = Game(
            sport="NCAAF",
            league="NCAAF",
            season=2026,
            provider_game_id=f"identity-game-{index}",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=now + timedelta(days=index),
        )
        db.add(game)
        db.flush()
        snapshot = Odds(
            game_id=game.id,
            sportsbook=f"Identity Book {index}",
            spread_home=-3.5 - index,
            spread_away=3.5 + index,
            spread_home_price=-110,
            spread_away_price=-110,
            moneyline_home=-200 - index,
            moneyline_away=180 + index,
            total=40.0 + index,
            total_over_price=-110,
            total_under_price=-110,
            created_at=now - timedelta(minutes=index),
        )
        db.add(snapshot)
        db.flush()
        prediction = Prediction(
            game_id=game.id,
            model_version="NPI-4.0",
            market=market,
            selection=selection,
            line_value=line,
            american_odds=price,
            odds_snapshot_id=snapshot.id,
            sportsbook=snapshot.sportsbook,
            odds_observed_at=snapshot.created_at,
            npi_score=190 - index,
            simulation_probability=85,
            confidence_score=90,
            projected_edge=8,
            risk_level="LOW",
            reasoning=f"Identity fixture {index}.",
        )
        db.add(prediction)
        db.flush()
        predictions.append(prediction)
        expected_games[game.id] = (home.name, away.name)

    db.commit()
    result = ParlayOptimizerService().build_parlay(
        db,
        leg_count=4,
        sport="NCAAF",
    )

    assert result["requested_leg_count"] == result["leg_count"] == 4
    assert result["adjustment_reason"] is None
    predictions_by_id = {prediction.id: prediction for prediction in predictions}

    assert {leg["prediction_id"] for leg in result["legs"]} == set(predictions_by_id)
    for leg in result["legs"]:
        prediction = predictions_by_id[leg["prediction_id"]]
        expected_home, expected_away = expected_games[prediction.game_id]

        assert leg["game_id"] == prediction.game_id
        assert leg["american_odds"] == prediction.american_odds
        assert leg["line_value"] == prediction.line_value
        assert leg["odds_snapshot_id"] == prediction.odds_snapshot_id
        assert leg["home_team"] == expected_home
        assert leg["away_team"] == expected_away
        assert leg["selection_reason"]

    legs_by_team = {leg["home_team"]: leg for leg in result["legs"]}
    assert legs_by_team["Nebraska"]["display_selection"] == "Nebraska ML -201"
    assert legs_by_team["Clemson"]["display_selection"] == "Duke ML +182"
    assert legs_by_team["Army"]["display_selection"] == (
        "Tarleton State at Army OVER 43"
    )


def test_optimizer_excludes_attractive_predictions_beyond_actionable_horizon():
    db = _session()
    now = datetime.now(UTC).replace(tzinfo=None)
    near_games = []
    for index, market in enumerate(("spread", "total", "moneyline"), start=1):
        game, _ = _add_candidate(db, index, market)
        game.game_date = now + timedelta(days=(1, 3, 6)[index - 1])
        near_games.append(game)

    army_navy, army_navy_prediction = _add_candidate(db, 4, "moneyline")
    army_navy.game_date = now + timedelta(days=102)
    army_navy_prediction.npi_score = 199
    army_navy_prediction.confidence_score = 99
    army_navy_prediction.simulation_probability = 0.95
    army_navy_prediction.projected_edge = 20.0
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)
    prediction_ids = {leg["prediction_id"] for leg in result["legs"]}

    assert army_navy_prediction.id not in prediction_ids
    assert result["horizon_days"] == 7
    assert result["generated_at"] >= now
    assert all(game.game_date <= now + timedelta(days=7) for game in near_games)


def test_optimizer_includes_upcoming_picks_on_the_next_slate():
    db = _session()
    now = datetime.now(UTC).replace(tzinfo=None)
    games = []
    for index, market in enumerate(("spread", "total"), start=1):
        game, _ = _add_candidate(db, index, market)
        game.game_date = now + timedelta(days=1)
        games.append(game)
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)

    assert {leg["game_id"] for leg in result["legs"]} == {game.id for game in games}
    assert all(leg["game_date"][:10] == (now + timedelta(days=1)).date().isoformat() for leg in result["legs"])


def test_parlay_moneyline_price_boundaries_and_other_markets():
    db = _session()
    fixtures = [
        _add_candidate(db, 1, "moneyline", american_odds=-400)[1],
        _add_candidate(db, 2, "moneyline", american_odds=-401)[1],
        _add_candidate(db, 3, "moneyline", american_odds=-1000)[1],
        _add_candidate(db, 4, "moneyline", american_odds=-20000)[1],
        _add_candidate(db, 5, "spread")[1],
        _add_candidate(db, 6, "total")[1],
    ]
    now = datetime.now(UTC).replace(tzinfo=None)

    candidates = ParlayOptimizerService()._load_candidates(
        db,
        sport=None,
        now=now,
        horizon_end=now + timedelta(days=7),
    )
    candidate_ids = {candidate["prediction_id"] for candidate in candidates}

    assert fixtures[0].id in candidate_ids
    assert fixtures[1].id not in candidate_ids
    assert fixtures[2].id not in candidate_ids
    assert fixtures[3].id not in candidate_ids
    assert fixtures[4].id in candidate_ids
    assert fixtures[5].id in candidate_ids


@pytest.mark.parametrize(
    ("case", "market", "selection", "line", "price", "expected"),
    [
        ("A", "spread", "HOME", -3.5, -110, True),
        ("B", "spread", "AWAY", 3.5, -110, True),
        ("C", "spread", "HOME", 3.5, -110, False),
        ("D", "spread", "AWAY", -3.5, -110, False),
        ("E", "spread", "HOME", None, -110, False),
        ("F", "spread", "HOME", -3.5, -105, True),
        ("G", "moneyline", "HOME", None, -150, True),
        ("H", "moneyline", "AWAY", None, 130, True),
        ("I", "moneyline", "HOME", None, 130, False),
        ("J", "moneyline", "AWAY", None, -150, False),
        ("K", "total", "OVER", 44.5, -110, True),
        ("L", "total", "UNDER", 44.5, -110, True),
        ("M", "total", "OVER", 45.5, -110, False),
        ("N", "total", "HOME", 44.5, -110, False),
        ("O", "total", "UNDER", 44.5, -105, True),
        ("P", "prop", "HOME", 44.5, -110, False),
    ],
    ids=lambda value: value if isinstance(value, str) and len(value) == 1 else None,
)
def test_frozen_snapshot_market_integrity(
    case,
    market,
    selection,
    line,
    price,
    expected,
):
    del case
    prediction = Prediction(
        market=market,
        selection=selection,
        line_value=line,
        american_odds=price,
    )
    odds = Odds(
        spread_home=-3.5,
        spread_away=3.5,
        spread_home_price=-110,
        spread_away_price=-110,
        moneyline_home=-150,
        moneyline_away=130,
        total=44.5,
        total_over_price=-110,
        total_under_price=-110,
    )

    assert ParlayOptimizerService._matches_frozen_snapshot(prediction, odds) is expected


def _candidate_ids(db):
    now = datetime.now(UTC).replace(tzinfo=None)
    return {
        candidate["prediction_id"]
        for candidate in ParlayOptimizerService()._load_candidates(
            db,
            sport=None,
            now=now,
            horizon_end=now + timedelta(days=7),
        )
    }


def test_q_optimizer_excludes_non_active_model_version():
    db = _session()
    _, prediction = _add_candidate(db, 1, "spread")
    prediction.model_version = "NPI-3.9"
    db.commit()

    assert prediction.id not in _candidate_ids(db)


def test_newer_odds_alone_does_not_supersede_a_coherent_prediction():
    db = _session()
    game, prediction = _add_candidate(db, 1, "spread")
    frozen_snapshot = db.get(Odds, prediction.odds_snapshot_id)
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="New Book",
            spread_home=-4.5,
            spread_away=4.5,
            spread_home_price=-110,
            spread_away_price=-110,
            moneyline_home=-175,
            moneyline_away=150,
            total=45.5,
            total_over_price=-110,
            total_under_price=-110,
            created_at=frozen_snapshot.created_at + timedelta(minutes=1),
        )
    )
    db.commit()

    assert prediction.id in _candidate_ids(db)


def test_changed_selected_side_quote_invalidates_prediction_until_recomputed():
    db = _session()
    game, prediction = _add_candidate(db, 1, "spread")
    frozen = db.get(Odds, prediction.odds_snapshot_id)
    db.add(
        Odds(
            game_id=game.id,
            sportsbook=prediction.sportsbook,
            spread_home=frozen.spread_home,
            spread_away=frozen.spread_away,
            spread_home_price=-108,
            spread_away_price=-112,
            moneyline_home=frozen.moneyline_home,
            moneyline_away=frozen.moneyline_away,
            total=frozen.total,
            total_over_price=frozen.total_over_price,
            total_under_price=frozen.total_under_price,
            created_at=frozen.created_at + timedelta(minutes=1),
        )
    )
    db.commit()

    assert prediction.id not in _candidate_ids(db)


def test_prediction_lifecycle_replacement_excludes_superseded_prediction():
    db = _session()
    game, old_prediction = _add_candidate(db, 1, "spread")
    old_snapshot = db.get(Odds, old_prediction.odds_snapshot_id)
    new_snapshot = Odds(
        game_id=game.id,
        sportsbook="New Book",
        spread_home=-4.5,
        spread_away=4.5,
        spread_home_price=-110,
        spread_away_price=-110,
        moneyline_home=-175,
        moneyline_away=150,
        total=45.5,
        total_over_price=-110,
        total_under_price=-110,
        created_at=old_snapshot.created_at + timedelta(minutes=1),
    )
    db.add(new_snapshot)
    db.flush()
    db.delete(old_prediction)
    db.flush()
    current_prediction = Prediction(
        game_id=game.id,
        model_version="NPI-4.0",
        market="spread",
        selection="HOME",
        line_value=new_snapshot.spread_home,
        american_odds=-110,
        odds_snapshot_id=new_snapshot.id,
        sportsbook=new_snapshot.sportsbook,
        odds_observed_at=new_snapshot.created_at,
        npi_score=170,
        simulation_probability=72,
        confidence_score=82,
        projected_edge=6,
        risk_level="LOW",
        reasoning="Current lifecycle replacement.",
    )
    db.add(current_prediction)
    db.commit()

    now = datetime.now(UTC).replace(tzinfo=None)
    candidates = ParlayOptimizerService()._load_candidates(
        db,
        sport=None,
        now=now,
        horizon_end=now + timedelta(days=7),
    )

    assert len(candidates) == 1
    assert candidates[0]["prediction_id"] == current_prediction.id
    assert candidates[0]["odds_snapshot_id"] == new_snapshot.id
    assert candidates[0]["odds_snapshot_id"] != old_snapshot.id


@pytest.mark.parametrize("status", ["final", "started", "postponed", "cancelled"])
def test_s_optimizer_excludes_non_scheduled_statuses(status):
    db = _session()
    game, prediction = _add_candidate(db, 1, "spread")
    game.status = status
    db.commit()

    assert prediction.id not in _candidate_ids(db)


def test_optimizer_uses_prediction_engine_fallback_without_active_model_configuration():
    db = _session()
    _, prediction = _add_candidate(db, 1, "spread")
    db.query(ModelRegistry).delete()
    db.commit()

    assert prediction.id in _candidate_ids(db)


def test_preferred_moneyline_outranks_equivalent_lower_priority_moneyline():
    db = _session()
    _, preferred = _add_candidate(db, 1, "moneyline", american_odds=-300)
    _, lower_priority = _add_candidate(db, 2, "moneyline", american_odds=-301)
    now = datetime.now(UTC).replace(tzinfo=None)
    lower_priority.npi_score = preferred.npi_score
    lower_priority.confidence_score = preferred.confidence_score
    lower_priority.simulation_probability = preferred.simulation_probability
    lower_priority.projected_edge = preferred.projected_edge
    lower_priority.risk_level = preferred.risk_level
    lower_priority.odds_observed_at = preferred.odds_observed_at

    preferred_score, _ = ParlayOptimizerService()._score(preferred, now)
    lower_priority_score, components = ParlayOptimizerService()._score(
        lower_priority,
        now,
    )

    assert preferred_score > lower_priority_score
    assert components["moneyline_price_adjustment"] == -0.01


def test_optimizer_falls_back_to_a_valid_two_leg_parlay_without_expanding_horizon():
    db = _session()
    now = datetime.now(UTC).replace(tzinfo=None)
    for index, market in enumerate(("spread", "total", "moneyline"), start=1):
        game, _ = _add_candidate(db, index, market)
        game.game_date = now + timedelta(days=index)

    distant_game, _ = _add_candidate(db, 4, "spread")
    distant_game.game_date = now + timedelta(days=102)
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=10)

    assert result["requested_leg_count"] == 10
    assert result["leg_count"] == 2
    assert result["adjustment_reason"]
    assert len({leg["game_id"] for leg in result["legs"]}) == 2
    assert all(leg["game_date"][:10] != distant_game.game_date.date().isoformat() for leg in result["legs"])


@pytest.mark.parametrize("version", ["NPI-4.0", "NPI-4.1", "NPI-5.0"])
def test_optimizer_includes_away_and_under_with_selected_side_metrics(version):
    db = _session()
    _, away = _add_candidate(db, 1, "spread", selection="AWAY", edge=15)
    _, under = _add_candidate(db, 2, "total", selection="UNDER", edge=3)
    away.model_version = under.model_version = version
    away.simulation_probability = 65 if version == "NPI-5.0" else 35
    if version == "NPI-5.0":
        away.projected_edge = 15
        under.projected_edge = 3
    db.commit()

    result = ParlayOptimizerService().build_parlay(db, leg_count=2)
    legs = {leg["prediction_id"]: leg for leg in result["legs"]}
    assert legs[away.id]["simulation_probability"] == 65
    assert legs[away.id]["selection"] == "AWAY"
    assert legs[away.id]["selected_side_edge"] == 15
    assert legs[under.id]["selection"] == "UNDER"
    assert legs[under.id]["selected_side_edge"] == 3
    assert result["average_projected_edge"] is None
    assert result["average_projected_edge_deprecated"] is True
    assert result["average_selected_side_edge_by_market"] == {
        "spread": {"value": 15, "unit": "percentage_points"},
        "total": {"value": 3, "unit": "scoring_points"},
    }


@pytest.mark.parametrize(("field", "value"), [
    ("confidence_score", None), ("simulation_probability", None),
    ("confidence_score", float("inf")), ("simulation_probability", 101),
    ("simulation_probability", float("nan")), ("npi_score", float("inf")),
    ("projected_edge", None), ("line_value", float("inf")),
    ("selection", ""), ("market", ""), ("american_odds", None),
    ("odds_snapshot_id", None),
])
def test_missing_parlay_metrics_are_excluded(field, value):
    db = _session()
    _, prediction = _add_candidate(db, 1, "spread")
    setattr(prediction, field, value)
    db.commit()
    now = datetime.now(UTC).replace(tzinfo=None)
    candidates = ParlayOptimizerService()._load_candidates(
        db, sport=None, now=now, horizon_end=now + timedelta(days=7),
    )
    assert candidates == []


def test_unclassified_parlay_risk_is_a_cached_client_safe_string():
    db = _session()
    _, first = _add_candidate(db, 1, "spread")
    _add_candidate(db, 2, "total")
    first.risk_level = None
    db.commit()
    result = ParlayOptimizerService().build_parlay(db, leg_count=2)
    assert result["risk_level"] == "unavailable"
    assert isinstance(result["average_confidence"], float)
    assert isinstance(result["average_model_probability"], float)
    assert all(isinstance(leg["simulation_probability"], float) for leg in result["legs"])


def test_optimize_route_forwards_requested_legs_and_sport(monkeypatch):
    from app.api.v1 import parlays as parlays_router

    fake_db = object()
    calls = []

    def override_db():
        yield fake_db

    class FakeOptimizer:
        def build_parlay(self, db, *, leg_count, sport=None):
            calls.append((db, leg_count, sport))
            return {"leg_count": leg_count, "sport": sport, "legs": []}

    app.dependency_overrides[parlays_router.get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role="admin",
        is_active=True,
    )
    monkeypatch.setattr(parlays_router, "ParlayOptimizerService", FakeOptimizer)

    try:
        response = TestClient(app).get("/api/v1/parlays/optimize?legs=6&sport=NFL")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["leg_count"] == 6
    assert calls == [(fake_db, 6, "NFL")]


def test_optimize_route_returns_smaller_valid_result_with_requested_count(monkeypatch):
    from app.api.v1 import parlays as parlays_router

    db = _session()
    for index, market in enumerate(("spread", "total", "moneyline", "spread"), start=1):
        _add_candidate(db, index, market)

    def override_db():
        yield db

    app.dependency_overrides[parlays_router.get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role="admin",
        is_active=True,
    )
    try:
        response = TestClient(app).get("/api/v1/parlays/optimize?legs=6")
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 200
    assert response.json()["requested_leg_count"] == 6
    assert response.json()["leg_count"] == 4
    assert response.json()["adjustment_reason"]
    assert len(response.json()["legs"]) == 4