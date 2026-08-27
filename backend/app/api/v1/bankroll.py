from fastapi import APIRouter, Depends

from app.auth.dependencies import require_viewer
from app.services.bankroll_service import BankrollService
from app.services.exposure_service import ExposureService
from app.services.kelly_service import KellyService

router = APIRouter(
    prefix="/bankroll",
    tags=["Bankroll"],
    dependencies=[Depends(require_viewer)],
)


@router.get("")
def get_bankroll():
    service = BankrollService()
    bankroll = {
        "total_amount": 10000,
        "unit_percentage": 0.01,
        "max_daily_risk": 0.05,
    }
    unit_size = service.calculate_unit_size(bankroll)
    available_risk = service.calculate_available_risk(bankroll)
    return {
        "total_amount": 10000,
        "unit_size": unit_size,
        "available_risk": available_risk,
    }


@router.post("")
def create_bankroll():
    return {"status": "created"}


@router.get("/bets/stake")
def get_stake():
    bankroll_service = BankrollService()
    kelly_service = KellyService()
    bankroll = {"total_amount": 10000, "unit_percentage": 0.01, "max_daily_risk": 0.05}
    unit_size = bankroll_service.calculate_unit_size(bankroll)
    fraction = kelly_service.calculate_fraction(2.5, 0.6)
    return {
        "recommended_stake": round(unit_size * (1 + fraction), 2),
        "units": round(1 + fraction, 2),
        "risk": "LOW",
        "reason": "High value with acceptable exposure",
    }


@router.get("/risk/exposure")
def get_exposure():
    exposure_service = ExposureService()
    return exposure_service.calculate_exposure(
        {
            "daily_risk": 500,
            "daily_limit": 750,
            "sport_exposure": {"NBA": 500},
            "team_exposure": {"BOS": 300},
            "market_exposure": {"ML": 200},
            "correlation_exposure": {},
        }
    )
