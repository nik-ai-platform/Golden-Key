from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.auth.dependencies import require_viewer
from app.auth.schemas import AuthUser
from app.main import app
from app.models.game import Game
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
    return sessionmaker(bind=engine)()


def _add_candidate(db, index, market, *, selection=None, stale=False, edge=6.0):
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
    odds = Odds(
        game_id=game.id,
        sportsbook="Test Book",
        spread_home=-3.5,
        spread_away=3.5,
        moneyline_home=-150,
        moneyline_away=130,
        total=44.5,
        created_at=observed_at,
    )
    db.add(odds)
    db.flush()
    if selection is None:
        selection = "OVER" if market == "total" and index % 2 else "HOME"
    prediction = Prediction(
        game_id=game.id,
        model_version="NPI-4.0",
        market=market,
        selection=selection,
        line_value=None if market == "moneyline" else (-3.5 if market == "spread" else 44.5),
        american_odds=-150 if market == "moneyline" else -110,
        odds_snapshot_id=odds.id,
        sportsbook=odds.sportsbook,
        odds_observed_at=observed_at,
        npi_score=170 - index,
        simulation_probability=72,
        confidence_score=82,
        projected_edge=edge,
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
def test_optimizer_enforces_market_mix_and_unique_games(
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
    assert all(0 <= leg["parlay_score"] <= 100 for leg in result["legs"])
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


def test_optimizer_preserves_prediction_game_snapshot_and_selected_price_identity():
    db = _session()
    fixtures = [
        ("Nebraska", "Cincinnati", "moneyline", "HOME", None, -145),
        ("Clemson", "Duke", "moneyline", "AWAY", None, 125),
        ("Army", "Tarleton State", "total", "OVER", 48.5, -108),
        ("Ohio", "Rutgers", "spread", "HOME", -3.5, -112),
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
            moneyline_home=-200 - index,
            moneyline_away=180 + index,
            total=40.0 + index,
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

    legs_by_team = {leg["home_team"]: leg for leg in result["legs"]}
    assert legs_by_team["Nebraska"]["display_selection"] == "Nebraska ML -145"
    assert legs_by_team["Clemson"]["display_selection"] == "Duke ML +125"
    assert legs_by_team["Army"]["display_selection"] == (
        "Tarleton State at Army OVER 48.5"
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


def test_optimizer_fails_instead_of_expanding_horizon_for_insufficient_inventory():
    db = _session()
    now = datetime.now(UTC).replace(tzinfo=None)
    for index, market in enumerate(("spread", "total", "moneyline"), start=1):
        game, _ = _add_candidate(db, index, market)
        game.game_date = now + timedelta(days=index)

    distant_game, _ = _add_candidate(db, 4, "spread")
    distant_game.game_date = now + timedelta(days=102)
    db.commit()

    with pytest.raises(
        ParlayOptimizationError,
        match="Not enough qualified predictions to build a 10-leg optimized parlay",
    ):
        ParlayOptimizerService().build_parlay(db, leg_count=10)


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
    app.dependency_overrides[require_viewer] = lambda: AuthUser(
        id=1,
        username="viewer",
        email="viewer@example.com",
        role="viewer",
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