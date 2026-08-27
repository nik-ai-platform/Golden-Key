from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_viewer
from app.services.alert_service import AlertService
from app.services.live_alert_service import LiveAlertService
from app.services.live_data_service import LiveDataService
from app.services.live_market_service import LiveMarketService
from app.services.live_npi_service import LiveNPIService
from app.services.live_odds_service import LiveOddsService
from app.services.live_prediction_service import LivePredictionService
from app.services.live_probability_service import LiveProbabilityService
from app.services.live_signal_service import LiveSignalService
from app.services.live_stream_service import LiveStreamService
from app.services import live_data_service


router = APIRouter(
    prefix="/live",
    tags=["Live Data"],
    dependencies=[Depends(require_viewer)],
)


@router.get("/games")
def get_live_games():
    service = LiveDataService()
    return service.get_live_games()


@router.get("/{game_id}")
def get_live_game(game_id: int):
    service = LiveDataService()
    return service.update_game_state({
        "game_id": game_id,
        "sport": "NBA",
        "quarter_period": "Q3",
        "time_remaining": "06:12",
        "home_score": 82,
        "away_score": 76,
        "possession": "HOME",
        "momentum_score": 7,
    })


@router.get("/probability/{game_id}")
def get_live_probability(game_id: int):
    service = LiveProbabilityService()
    return {"game_id": game_id, **service.estimate_probabilities(0.68, 0.62, 0.58)}


@router.get("/signals")
def get_live_signals():
    service = LiveSignalService()
    return service.generate_signal("VALUE", {"team": "Denver", "market": "+5", "model": "72% cover"})


@router.get("/alerts")
def get_live_alerts():
    service = LiveAlertService()
    return service.create_alert("Probability Shift", {"message": "Celtics probability increased 14%"})


@router.get("/stream")
def get_live_stream():
    service = LiveStreamService()
    return service.publish({"event": "live_update", "status": "streaming"})


@router.get("/value")
def get_live_value():
    prediction_service = LivePredictionService()
    result = prediction_service.predict_live_outcome({"team": "Boston Celtics", "momentum": 22})
    return {
        "game": "Boston vs Miami",
        "live_edge": 9.4,
        "recommendation": "BET",
        "confidence": result["confidence"],
    }


@router.get("/alerts")
def get_alerts():
    service = AlertService()
    return service.create_alert(
        "Value Opportunity",
        {"message": "Celtics ML", "value": "HIGH", "confidence": 84},
    )


@router.get("/{sport}")
def get_live_data(
    sport: str
):
    try:
        return live_data_service.get_live_odds(sport)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch live data: {exc}"
        )
