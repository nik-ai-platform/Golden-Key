from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.repositories import game_repository
from app.services.closing_line_value_service import ClosingLineValueService
from app.services.clv_service import CLVService
from app.services.line_shopping_service import LineShoppingService
from app.services.market_data_service import MarketDataService
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.market_movement_service import MarketMovementService
from app.services.value_alert_service import ValueAlertService


router = APIRouter(
    prefix="/market",
    tags=["Market"],
    dependencies=[Depends(require_analyst)],
)


market_service = MarketIntelligenceService()
clv_service = ClosingLineValueService(market_intelligence_service=market_service)


@router.get("/value/{game_id}")
def market_value(game_id: int, db: Session = Depends(get_db)):
    game = game_repository.get_game_with_teams(db, game_id)
    prediction = None
    if hasattr(db, "query"):
        from app.models.nik_score import NikScore

        prediction = (
            db.query(NikScore)
            .filter(NikScore.game_id == game_id)
            .order_by(NikScore.id.desc())
            .first()
        )

    if game is None or prediction is None:
        return {
            "game": str(game_id),
            "spread_edge": 0.0,
            "moneyline_edge": 0.0,
            "value_score": 0.0,
            "recommendation": "hold",
        }

    evaluation = market_service.evaluate_game(db, game, prediction) or {
        "spread_edge": 0.0,
        "moneyline_edge": 0.0,
        "value_score": 0.0,
        "recommendation": "hold",
    }
    return {
        "game": f"{game.home_team.name} vs {game.away_team.name}",
        "spread_edge": evaluation.get("spread_edge", 0.0),
        "moneyline_edge": evaluation.get("moneyline_edge", 0.0),
        "value_score": evaluation.get("value_score", 0.0),
        "recommendation": evaluation.get("recommendation", "hold"),
    }


@router.get("/movers")
def market_movers(db: Session = Depends(get_db)):
    return market_service.market_movers(db)


@router.get("/{game_id}")
def get_market(game_id: int):
    service = MarketDataService()
    return service.get_market_snapshot(game_id)


@router.get("/best-lines")
def get_best_lines():
    service = LineShoppingService()
    return service.find_best_line("Lakers vs Celtics", [
        {"book": "Book A", "line": "Lakers -4.5", "price": "-110"},
        {"book": "Book B", "line": "Lakers -4", "price": "-105"},
        {"book": "Book C", "line": "Lakers -5", "price": "-115"},
    ])


@router.get("/movement")
def get_movement():
    service = MarketMovementService()
    return service.detect_movement(2, 5)


@router.get("/value-alerts")
def get_value_alerts():
    service = ValueAlertService()
    return service.check(6, 4.5)


@router.get("/clv")
def market_clv(db: Session = Depends(get_db)):
    return market_service.clv_summary(db)


@router.get("/clv-summary")
def get_clv_summary():
    service = CLVService()
    return service.summarize([{"clv": 2}, {"clv": 1.5}])
