from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.odds import Odds  # noqa: F401
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team  # noqa: F401
from app.models.user import User
from app.models.user_prediction import UserPrediction
from app.services.live_data_service import LiveDataService
from app.services.npi_engine import NPIEngine
from app.services.odds_service import NoCompleteOddsSnapshotError
from app.services.prediction_engine import PredictionEngine
from app.services.v1_read_service import V1ReadService
from app.workers.game_importer import GameOddsImporter


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _event(with_odds=False):
    event = {
        "id": "ncaaf-provider-game-1",
        "home_team": "Texas Longhorns",
        "away_team": "Ohio State Buckeyes",
        "commence_time": "2026-09-10T19:30:00Z",
        "bookmakers": [],
    }
    if with_odds:
        event["bookmakers"] = [
            {
                "title": "Test Sportsbook",
                "markets": [
                    {
                        "key": "h2h",
                        "outcomes": [
                            {"name": event["home_team"], "price": -280},
                            {"name": event["away_team"], "price": 230},
                        ],
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": event["home_team"], "point": -7.5},
                            {"name": event["away_team"], "point": 7.5},
                        ],
                    },
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 52.5},
                            {"name": "Under", "point": 52.5},
                        ],
                    },
                ],
            }
        ]
    return event


def _odds():
    return SimpleNamespace(
        spread_home=-7.5,
        spread_away=7.5,
        moneyline_home=-280,
        moneyline_away=230,
        total=52.5,
    )


def _configured_prediction_engine():
    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: NCAAF"
    )
    engine.ai_engine = MagicMock()
    engine.ai_engine.generate_analysis.return_value = {
        "engine_version": "test",
        "summary": "NCAAF test analysis",
        "explanation": "NCAAF test analysis",
    }
    return engine


def _legacy_predictions(game_id):
    return [
        Prediction(
            game_id=game_id,
            model_version="NPI-4.0",
            market=market,
            selection=selection,
            line_value=line_value,
            american_odds=american_odds,
            npi_score=120,
            confidence_score=70,
            projected_edge=5,
        )
        for market, selection, line_value, american_odds in (
            ("spread", "HOME", -6.5, -110),
            ("moneyline", "HOME", None, -250),
            ("total", "OVER", 51.5, -110),
        )
    ]


def test_live_data_maps_ncaaf_to_provider_identifier(monkeypatch):
    response = MagicMock()
    response.json.return_value = []
    request = MagicMock(return_value=response)
    monkeypatch.setattr("app.services.live_data_service.requests.get", request)

    LiveDataService().fetch_games("NCAAF")

    assert request.call_args.args[0].endswith(
        "/americanfootball_ncaaf/odds"
    )


def test_live_data_preserves_existing_provider_identifier(monkeypatch):
    response = MagicMock()
    response.json.return_value = []
    request = MagicMock(return_value=response)
    monkeypatch.setattr("app.services.live_data_service.requests.get", request)

    LiveDataService().fetch_games("baseball_mlb")

    assert request.call_args.args[0].endswith("/baseball_mlb/odds")


def test_ncaaf_import_is_idempotent_by_provider_game_id():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event()]
    importer = GameOddsImporter(db=db, live_data_service=live_data)

    first = importer.import_games("NCAAF")
    second = importer.import_games("NCAAF")

    games = db.query(Game).all()
    assert len(games) == 1
    assert first[0].id == second[0].id == games[0].id
    assert games[0].provider_game_id == "ncaaf-provider-game-1"
    assert games[0].sport == "NCAAF"


def test_incomplete_future_prediction_set_is_replaced_from_exact_snapshot():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event()]
    game = GameOddsImporter(db=db, live_data_service=live_data).import_games("NCAAF")[0]
    game.game_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    existing = _legacy_predictions(game.id)
    db.add_all(existing)
    db.commit()
    assert all(prediction.odds_snapshot_id is None for prediction in existing)

    selected_snapshot = Odds(
        game_id=game.id,
        sportsbook="Current Sportsbook",
        spread_home=-7.5,
        spread_away=7.5,
        moneyline_home=-280,
        moneyline_away=230,
        total=52.5,
    )
    db.add(selected_snapshot)
    db.commit()

    engine = _configured_prediction_engine()
    regenerated = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    stored = db.query(Prediction).filter(Prediction.game_id == game.id).all()

    assert len(regenerated) == len(stored) == 3
    assert {prediction.market for prediction in stored} == {
        "spread",
        "moneyline",
        "total",
    }
    assert all(
        prediction.odds_snapshot_id == selected_snapshot.id
        for prediction in stored
    )
    by_market = {prediction.market: prediction for prediction in stored}
    expected_spread = (
        selected_snapshot.spread_away
        if by_market["spread"].selection == "AWAY"
        else selected_snapshot.spread_home
    )
    expected_moneyline = (
        selected_snapshot.moneyline_away
        if by_market["moneyline"].selection == "AWAY"
        else selected_snapshot.moneyline_home
    )
    assert by_market["spread"].line_value == expected_spread
    assert by_market["moneyline"].american_odds == expected_moneyline
    assert by_market["total"].line_value == selected_snapshot.total

    regenerated_ids = {prediction.id for prediction in regenerated}
    repeated = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    assert {prediction.id for prediction in repeated} == regenerated_ids
    assert db.query(Prediction).filter(Prediction.game_id == game.id).count() == 3


def test_snapshot_selection_uses_sportsbook_priority_not_insertion_order():
    observed_at = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(
            id=99,
            sportsbook="Fanatics",
            created_at=observed_at,
            spread_home=-7.5,
            spread_away=7.5,
            moneyline_home=-280,
            moneyline_away=230,
            total=52.5,
        ),
        SimpleNamespace(
            id=1,
            sportsbook="DraftKings",
            created_at=observed_at,
            spread_home=-8.0,
            spread_away=8.0,
            moneyline_home=-300,
            moneyline_away=240,
            total=53.0,
        ),
    ]

    selected = PredictionEngine._select_complete_snapshot(rows)

    assert selected.sportsbook == "DraftKings"


def test_snapshot_selection_prefers_newest_batch_before_sportsbook():
    observed_at = datetime.now(timezone.utc)
    rows = [
        SimpleNamespace(
            id=1,
            sportsbook="DraftKings",
            created_at=observed_at,
            spread_home=-7.5,
            spread_away=7.5,
            moneyline_home=-280,
            moneyline_away=230,
            total=52.5,
        ),
        SimpleNamespace(
            id=2,
            sportsbook="Fanatics",
            created_at=observed_at + timedelta(minutes=1),
            spread_home=-8.0,
            spread_away=8.0,
            moneyline_home=-300,
            moneyline_away=240,
            total=53.0,
        ),
    ]

    selected = PredictionEngine._select_complete_snapshot(rows)

    assert selected.sportsbook == "Fanatics"


def test_saved_future_predictions_are_not_refreshed():
    db = _session()
    game = GameOddsImporter(
        db=db,
        live_data_service=MagicMock(fetch_games=MagicMock(return_value=[_event()])),
    ).import_games("NCAAF")[0]
    game.game_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    first_snapshot = Odds(
        game_id=game.id,
        sportsbook="Fanatics",
        spread_home=-7.5,
        spread_away=7.5,
        moneyline_home=-280,
        moneyline_away=230,
        total=52.5,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(first_snapshot)
    db.commit()
    engine = _configured_prediction_engine()
    predictions = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    user = User(
        username="snapshot-owner",
        email="snapshot-owner@example.com",
        hashed_password="test",
    )
    db.add(user)
    db.flush()
    db.add(UserPrediction(user_id=user.id, prediction_id=predictions[0].id))
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="DraftKings",
            spread_home=-9.5,
            spread_away=9.5,
            moneyline_home=-400,
            moneyline_away=320,
            total=56.5,
            created_at=first_snapshot.created_at + timedelta(minutes=1),
        )
    )
    db.commit()

    returned = engine.analyze_markets(db=db, game_id=game.id, persist=True)

    assert {prediction.id for prediction in returned} == {
        prediction.id for prediction in predictions
    }
    assert all(
        prediction.odds_snapshot_id == first_snapshot.id
        for prediction in returned
    )


def test_settled_legacy_predictions_and_results_are_never_regenerated():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event()]
    game = GameOddsImporter(db=db, live_data_service=live_data).import_games("NCAAF")[0]
    game.game_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    game.status = "final"
    predictions = _legacy_predictions(game.id)
    db.add_all(predictions)
    db.flush()
    results = [
        PredictionResult(
            prediction_id=prediction.id,
            actual_result="HOME",
            predicted_result=prediction.selection,
            outcome="WIN",
            profit_loss=10,
        )
        for prediction in predictions
    ]
    db.add_all(results)
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="Later Sportsbook",
            spread_home=-8.5,
            spread_away=8.5,
            moneyline_home=-320,
            moneyline_away=260,
            total=54.5,
        )
    )
    db.commit()
    prediction_ids = {prediction.id for prediction in predictions}
    result_ids = {result.id for result in results}

    returned = _configured_prediction_engine().analyze_markets(
        db=db,
        game_id=game.id,
        persist=True,
    )

    assert {prediction.id for prediction in returned} == prediction_ids
    assert {prediction.id for prediction in db.query(Prediction).all()} == prediction_ids
    assert {result.id for result in db.query(PredictionResult).all()} == result_ids


def test_incomplete_bookmaker_snapshot_is_not_persisted():
    event = _event(with_odds=True)
    event["bookmakers"][0]["markets"] = [
        market
        for market in event["bookmakers"][0]["markets"]
        if market["key"] != "h2h"
    ]
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [event]

    game = GameOddsImporter(
        db=db,
        live_data_service=live_data,
    ).import_games("NCAAF")[0]

    assert db.query(Game).filter(Game.id == game.id).one()
    assert db.query(Odds).filter(Odds.game_id == game.id).all() == []


@pytest.mark.parametrize(
    ("spread_home", "spread_away"),
    [(-5.5, 5.5), (3.5, -3.5)],
)
def test_import_orients_spreads_by_team_name_not_outcome_order(
    spread_home,
    spread_away,
):
    event = _event(with_odds=True)
    spread_market = next(
        market
        for market in event["bookmakers"][0]["markets"]
        if market["key"] == "spreads"
    )
    spread_market["outcomes"] = [
        {"name": event["away_team"], "point": spread_away},
        {"name": event["home_team"], "point": spread_home},
    ]
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [event]

    game = GameOddsImporter(db=db, live_data_service=live_data).import_games("WNBA")[0]
    odds = db.query(Odds).filter(Odds.game_id == game.id).one()

    assert odds.spread_home == spread_home
    assert odds.spread_away == spread_away


def test_incomplete_bookmakers_cannot_be_mixed_into_one_snapshot():
    event = _event(with_odds=True)
    first, second = event["bookmakers"][0].copy(), event["bookmakers"][0].copy()
    first["title"] = "Spread Only"
    first["markets"] = [
        market for market in event["bookmakers"][0]["markets"]
        if market["key"] == "spreads"
    ]
    second["title"] = "Prices Only"
    second["markets"] = [
        market for market in event["bookmakers"][0]["markets"]
        if market["key"] != "spreads"
    ]
    event["bookmakers"] = [first, second]
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [event]

    GameOddsImporter(db=db, live_data_service=live_data).import_games("WNBA")

    assert db.query(Odds).count() == 0


@pytest.mark.parametrize("with_incomplete_history", [False, True])
def test_engine_reports_no_complete_snapshot_semantically(
    with_incomplete_history,
):
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event()]
    game = GameOddsImporter(
        db=db,
        live_data_service=live_data,
    ).import_games("NCAAF")[0]

    if with_incomplete_history:
        db.add(
            Odds(
                game_id=game.id,
                sportsbook="Historical Incomplete Book",
                spread_home=-7.5,
                spread_away=7.5,
                moneyline_home=None,
                moneyline_away=None,
                total=52.5,
            )
        )
        db.commit()

    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: NCAAF"
    )

    with pytest.raises(NoCompleteOddsSnapshotError):
        engine.analyze_markets(
            db=db,
            game_id=game.id,
            persist=True,
        )


def test_ncaaf_uses_default_npi_profile_and_stays_on_200_point_scale(
    monkeypatch,
):
    def missing_profile(db, sport, model_version):
        raise ValueError(
            "No NPI weight profile found for NCAAF NPI-4.0"
        )

    monkeypatch.setattr(
        NPIEngine.weight_profiles,
        "get_profile",
        missing_profile,
    )

    result = NPIEngine().calculate(
        db=object(),
        game=SimpleNamespace(),
        odds=_odds(),
        sport="NCAAF",
        model_version="NPI-4.0",
    )

    assert 0 <= result["npi_score"] <= 200
    assert [factor["weight"] for factor in result["factors"]] == list(
        NPIEngine.DEFAULT_WEIGHTS.values()
    )


def test_ncaaf_builds_unified_spread_moneyline_and_total_predictions():
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.side_effect = [
        {
            "win_probability": 62,
            "runs": 10000,
            "average_margin": 4.0,
        },
        {
            "win_probability": 58,
            "runs": 10000,
            "average_margin": 2.0,
        },
    ]

    specifications = engine._market_specifications(
        sport="NCAAF",
        odds=_odds(),
        spread_npi={"npi_score": 110, "factors": []},
    )

    assert [item["market"] for item in specifications] == [
        "spread",
        "moneyline",
        "total",
    ]
    assert all(0 <= item["npi_score"] <= 200 for item in specifications)
    assert specifications[0]["line_value"] is not None
    assert specifications[1]["american_odds"] is not None
    assert specifications[2]["line_value"] == 52.5


def test_moneyline_upset_signal_shadows_historical_rule_without_changing_pick():
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.return_value = {
        "win_probability": 42,
        "runs": 10000,
        "average_margin": -2.0,
    }
    spread_npi = {
        "npi_score": 110,
        "factors": [
            {
                "name": "Historical Rule Engine",
                "weight": 80,
                "score": 28,
                "explanation": "Spreadsheet-origin rule match",
            }
        ],
    }

    moneyline = engine._moneyline_specification(_odds(), spread_npi)

    assert moneyline["upset_signal"] == 35.0
    assert moneyline["selection"] == "AWAY"
    assert moneyline["american_odds"] == 230


def test_moneyline_upset_signal_is_missing_without_independent_rule_factor():
    engine = PredictionEngine()
    engine.simulation_engine = MagicMock()
    engine.simulation_engine.simulate.return_value = {
        "win_probability": 42,
        "runs": 10000,
        "average_margin": -2.0,
    }

    moneyline = engine._moneyline_specification(
        _odds(),
        {"npi_score": 110, "factors": []},
    )

    assert moneyline["upset_signal"] is None


@pytest.mark.parametrize(
    ("spread_home", "spread_away", "selection", "expected_line"),
    [
        (-5.5, 5.5, "HOME", -5.5),
        (3.5, -3.5, "AWAY", -3.5),
        (3.5, -3.5, "HOME", 3.5),
    ],
)
def test_prediction_uses_selected_team_spread(
    spread_home,
    spread_away,
    selection,
    expected_line,
):
    odds = _odds()
    odds.spread_home = spread_home
    odds.spread_away = spread_away
    engine = PredictionEngine()
    engine.determine_pick = MagicMock(return_value=selection)

    spread = engine._market_specifications(
        sport="WNBA",
        odds=odds,
        spread_npi={"npi_score": 110, "factors": []},
    )[0]

    assert spread["selection"] == selection
    assert spread["line_value"] == expected_line


def test_one_ncaaf_event_persists_complete_odds_and_three_predictions():
    db = _session()
    live_data = MagicMock()
    live_data.fetch_games.return_value = [_event(with_odds=True)]
    game = GameOddsImporter(
        db=db,
        live_data_service=live_data,
    ).import_games("NCAAF")[0]
    db.add(
        Odds(
            game_id=game.id,
            sportsbook="Incomplete Sportsbook",
            spread_home=-7.0,
            spread_away=7.0,
            moneyline_home=None,
            moneyline_away=None,
            total=53.0,
        )
    )
    db.commit()

    engine = PredictionEngine()
    engine.model_runtime = MagicMock()
    engine.model_runtime.resolve.side_effect = ValueError(
        "No production model configured for sport: NCAAF"
    )
    engine.ai_engine = MagicMock()
    engine.ai_engine.generate_analysis.return_value = {
        "engine_version": "test",
        "summary": "NCAAF test analysis",
        "explanation": "NCAAF test analysis",
    }

    predictions = engine.analyze_markets(
        db=db,
        game_id=game.id,
        persist=True,
    )

    stored_game = db.query(Game).filter(Game.id == game.id).one()
    stored_odds = (
        db.query(Odds)
        .filter(
            Odds.game_id == game.id,
            Odds.spread_home.is_not(None),
            Odds.spread_away.is_not(None),
            Odds.moneyline_home.is_not(None),
            Odds.moneyline_away.is_not(None),
            Odds.total.is_not(None),
        )
        .one()
    )
    stored_predictions = (
        db.query(Prediction)
        .filter(Prediction.game_id == game.id)
        .all()
    )
    assert stored_game.provider_game_id == "ncaaf-provider-game-1"
    assert stored_game.sport == "NCAAF"
    assert (
        stored_odds.spread_home,
        stored_odds.spread_away,
        stored_odds.moneyline_home,
        stored_odds.moneyline_away,
        stored_odds.total,
    ) == (-7.5, 7.5, -280, 230, 52.5)
    assert [prediction.market for prediction in predictions] == [
        "spread",
        "moneyline",
        "total",
    ]
    assert len(stored_predictions) == 3
    assert all(0 <= prediction.npi_score <= 200 for prediction in predictions)
    assert all(
        prediction.odds_snapshot_id == stored_odds.id
        and prediction.sportsbook == stored_odds.sportsbook
        and prediction.odds_observed_at == stored_odds.created_at
        for prediction in predictions
    )
    assert next(
        prediction.upset_signal
        for prediction in predictions
        if prediction.market == "moneyline"
    ) == 25.0
    assert all(
        prediction.upset_signal is None
        for prediction in predictions
        if prediction.market != "moneyline"
    )

    original_lines = {
        prediction.market: prediction.line_value
        for prediction in predictions
    }
    later_snapshot = Odds(
        game_id=game.id,
        sportsbook="Later Sportsbook",
        spread_home=-20.0,
        spread_away=20.0,
        moneyline_home=-900,
        moneyline_away=650,
        total=60.0,
        created_at=stored_odds.created_at + timedelta(minutes=1),
    )
    db.add(later_snapshot)
    db.commit()
    repeated = engine.analyze_markets(db=db, game_id=game.id, persist=True)
    refreshed_lines = {
        prediction.market: prediction.line_value
        for prediction in repeated
    }
    assert refreshed_lines != original_lines
    assert refreshed_lines["total"] == later_snapshot.total
    assert all(
        prediction.odds_snapshot_id == later_snapshot.id
        for prediction in repeated
    )

    feed = V1ReadService().get_today_predictions(
        db=db,
        sport="NCAAF",
        include_passes=True,
    )
    assert feed["sport"] == "NCAAF"
    assert feed["slate_date"] == "2026-09-10"
    assert feed["count"] == 3
    assert {item["market"] for item in feed["predictions"]} == {
        "spread",
        "moneyline",
        "total",
    }

    unfiltered_feed = V1ReadService().get_today_predictions(
        db=db,
        include_passes=True,
    )
    daily_card = V1ReadService().get_daily_card(db=db)
    assert unfiltered_feed["slate_date"] == feed["slate_date"]
    assert unfiltered_feed["count"] == 3
    assert daily_card["slate_date"] == feed["slate_date"]
    assert daily_card["count"] == 3

    stored_game.status = "final"
    db.commit()
    assert V1ReadService().get_today_predictions(
        db=db,
        sport="NCAAF",
        include_passes=True,
    )["count"] == 0