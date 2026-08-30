from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.result_settlement_service import ResultSettlementService


def _game(home_score, away_score, sport="WNBA", league="WNBA"):
    return SimpleNamespace(
        id=123,
        home_score=home_score,
        away_score=away_score,
        sport=sport,
        league=league,
    )


def _prediction(market, selection, line_value, american_odds=-110):
    return SimpleNamespace(
        id=502,
        market=market,
        selection=selection,
        line_value=line_value,
        american_odds=american_odds,
    )


def test_win_profit_at_minus_110():
    service = ResultSettlementService()

    result = service.calculate_profit_loss(
        outcome="WIN",
        american_odds=-110,
        stake=110,
    )

    assert result == 100.0


def test_loss_returns_negative_stake():
    service = ResultSettlementService()

    result = service.calculate_profit_loss(
        outcome="LOSS",
        american_odds=-110,
        stake=100,
    )

    assert result == -100.0


def test_push_returns_zero():
    service = ResultSettlementService()

    result = service.calculate_profit_loss(
        outcome="PUSH",
        american_odds=-110,
        stake=100,
    )

    assert result == 0.0


def test_spread_uses_snapshot_line_without_current_odds():
    db = MagicMock()
    result = ResultSettlementService().grade_prediction(
        db=db,
        game=_game(home_score=92, away_score=85),
        prediction=_prediction("spread", "HOME", -9, 120),
    )

    assert result["outcome"] == "LOSS"
    assert result["profit_loss"] == -100.0
    db.query.assert_not_called()


def test_moneyline_uses_snapshot_price():
    result = ResultSettlementService().grade_prediction(
        db=MagicMock(),
        game=_game(home_score=92, away_score=85),
        prediction=_prediction("moneyline", "HOME", None, 150),
    )

    assert result["outcome"] == "WIN"
    assert result["profit_loss"] == 150.0


def test_total_uses_snapshot_line_without_current_odds():
    db = MagicMock()
    result = ResultSettlementService().grade_prediction(
        db=db,
        game=_game(home_score=84, away_score=81),
        prediction=_prediction("total", "UNDER", 172.5),
    )

    assert result["outcome"] == "WIN"
    db.query.assert_not_called()


def test_spread_and_total_push_on_exact_snapshot_line():
    service = ResultSettlementService()

    spread = service.grade_prediction(
        db=MagicMock(),
        game=_game(home_score=92, away_score=83),
        prediction=_prediction("spread", "HOME", -9),
    )
    total = service.grade_prediction(
        db=MagicMock(),
        game=_game(home_score=84, away_score=81),
        prediction=_prediction("total", "UNDER", 165),
    )

    assert spread["outcome"] == "PUSH"
    assert total["outcome"] == "PUSH"


def test_missing_prediction_snapshot_is_rejected():
    service = ResultSettlementService()

    try:
        service.grade_prediction(
            db=MagicMock(),
            game=_game(home_score=92, away_score=85),
            prediction=_prediction("spread", "HOME", None),
        )
    except ValueError as error:
        assert str(error) == "Prediction 502 has no spread line snapshot"
    else:
        raise AssertionError("Missing spread snapshot was accepted")


def test_moneyline_tie_is_rejected_for_sport_that_cannot_tie():
    service = ResultSettlementService()

    try:
        service.grade_prediction(
            db=MagicMock(),
            game=_game(home_score=85, away_score=85, sport="NBA", league="NBA"),
            prediction=_prediction("moneyline", "HOME", None),
        )
    except ValueError as error:
        assert str(error) == "Game 123 cannot have a tied moneyline result"
    else:
        raise AssertionError("Tied NBA moneyline was graded as a push")


def test_moneyline_tie_pushes_for_tie_capable_game():
    result = ResultSettlementService().grade_prediction(
        db=MagicMock(),
        game=_game(home_score=1, away_score=1, sport="SOCCER", league="MLS"),
        prediction=_prediction("moneyline", "HOME", None),
    )

    assert result["outcome"] == "PUSH"


def test_settle_game_persists_and_reports_all_three_markets():
    game = _game(home_score=84, away_score=81)
    predictions = [
        _prediction("spread", "HOME", -3),
        _prediction("moneyline", "AWAY", None, 150),
        _prediction("total", "UNDER", 165),
    ]
    for prediction_id, prediction in enumerate(predictions, start=501):
        prediction.id = prediction_id

    game_query = MagicMock()
    game_query.filter.return_value.first.return_value = game
    prediction_query = MagicMock()
    prediction_query.filter.return_value.all.return_value = predictions
    result_queries = [MagicMock() for _ in predictions]
    for result_query in result_queries:
        result_query.filter.return_value.first.return_value = None

    db = MagicMock()
    db.query.side_effect = [game_query, prediction_query, *result_queries]

    response = ResultSettlementService().settle_game(db=db, game_id=game.id)

    assert response["game_id"] == game.id
    assert response["settled"] == 3
    assert [
        {"market": item["market"], "result": item["result"]}
        for item in response["results"]
    ] == [
        {"market": "spread", "result": "PUSH"},
        {"market": "moneyline", "result": "LOSS"},
        {"market": "total", "result": "PUSH"},
    ]
    assert [call.args[0].outcome for call in db.add.call_args_list] == [
        "PUSH",
        "LOSS",
        "PUSH",
    ]
    db.commit.assert_called_once_with()


def test_existing_result_is_not_settled_twice():
    game = SimpleNamespace(
        id=123,
        home_score=88,
        away_score=80,
    )
    prediction = SimpleNamespace(
        id=502,
        market="spread",
    )
    existing = SimpleNamespace(outcome="WIN")

    game_query = MagicMock()
    game_query.filter.return_value.first.return_value = game
    prediction_query = MagicMock()
    prediction_query.filter.return_value.all.return_value = [prediction]
    result_query = MagicMock()
    result_query.filter.return_value.first.return_value = existing
    db = MagicMock()
    db.query.side_effect = [
        game_query,
        prediction_query,
        result_query,
    ]

    result = ResultSettlementService().settle_game(
        db=db,
        game_id=123,
    )

    assert result == {
        "game_id": 123,
        "settled": 0,
        "results": [
            {
                "prediction_id": 502,
                "status": "already_settled",
                "outcome": "WIN",
            }
        ],
    }
    db.add.assert_not_called()
