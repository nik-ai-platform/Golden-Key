from app.services.bankroll_service import BankrollService
from app.services.exposure_service import ExposureService
from app.services.kelly_service import KellyService


def test_unit_sizing_is_accurate():
    service = BankrollService()
    bankroll = {"total_amount": 10000, "unit_percentage": 0.01}

    assert service.calculate_unit_size(bankroll) == 100.0


def test_kelly_never_exceeds_limits():
    service = KellyService()
    fraction = service.calculate_fraction(2.5, 0.6)

    assert fraction <= 0.25


def test_exposure_limits_trigger_correctly():
    service = ExposureService()
    result = service.calculate_exposure({"daily_risk": 800, "daily_limit": 750})

    assert result["status"] == "Blocked"


def test_losing_bets_update_bankroll():
    service = BankrollService()
    result = service.update_balance({"current_balance": 10000, "net_change": -125})

    assert result == 9875.0


def test_high_risk_bets_reduce_stake():
    service = ExposureService()
    adjusted = service.apply_risk_rules(300, 80, 150)

    assert adjusted == 75.0


def test_missing_bankroll_data_is_handled_safely():
    service = BankrollService()

    assert service.calculate_unit_size(None) == 0
    assert service.calculate_available_risk(None) == 0
    assert service.update_balance(None) == 0
