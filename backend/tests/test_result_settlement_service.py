from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.result_settlement_service import ResultSettlementService


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
