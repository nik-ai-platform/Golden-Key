"""Customer offers approved for sandbox launch validation."""

from typing import Literal, TypedDict


class LaunchPlan(TypedDict):
    id: str
    name: str
    amount_minor: int
    interval: Literal["month", "year"]


class PublicLaunchPlans(TypedDict):
    currency: str
    trial_days: int
    plans: list[LaunchPlan]
    premium_benefits: list[str]


LAUNCH_PLANS: dict[str, LaunchPlan] = {
    "pro_monthly": {
        "id": "pro_monthly", "name": "Bear A Hand Pro Monthly",
        "amount_minor": 999, "interval": "month",
    },
    "pro_annual": {
        "id": "pro_annual", "name": "Bear A Hand Pro Annual",
        "amount_minor": 8999, "interval": "year",
    },
}
LAUNCH_CURRENCY = "USD"
LAUNCH_TRIAL_DAYS = 7
PREMIUM_BENEFITS = [
    "Full picks and odds", "Game analysis", "Saved picks",
    "Parlay optimizer", "Performance intelligence",
]


def public_launch_plans() -> PublicLaunchPlans:
    return {
        "currency": LAUNCH_CURRENCY,
        "trial_days": LAUNCH_TRIAL_DAYS,
        "plans": [plan.copy() for plan in LAUNCH_PLANS.values()],
        "premium_benefits": PREMIUM_BENEFITS.copy(),
    }
