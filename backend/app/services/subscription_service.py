from sqlalchemy.orm import Session

from app.models.subscription import Subscription


def create_free_subscription(
    db: Session,
    user_id: int
):

    existing = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id
        )
        .first()
    )

    if existing:

        return existing

    subscription = Subscription(

        user_id=user_id,

        plan="free",

        active=True

    )

    db.add(subscription)

    db.commit()

    db.refresh(subscription)

    return subscription


def get_user_subscription(
    db: Session,
    user_id: int
):

    subscription = (

        db.query(Subscription)

        .filter(
            Subscription.user_id ==
            user_id
        )

        .first()

    )

    if subscription:

        return subscription

    return {
        "id": None,
        "plan": "free",
        "active": False,
        "created_at": None,
    }


def upgrade_subscription(
    db: Session,
    user_id: int,
    plan: str
):

    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id
        )
        .first()
    )

    if not subscription:

        subscription = create_free_subscription(
            db,
            user_id
        )

    subscription.plan = plan

    db.commit()

    db.refresh(subscription)

    return subscription


class SubscriptionService:

    PLANS = ["FREE", "PRO", "ELITE", "ENTERPRISE"]

    def features_for(
        self,
        plan: str
    ) -> list[str]:

        normalized = (plan or "FREE").upper()

        if normalized == "ENTERPRISE":

            return [
                "Unlimited Research",
                "API Access",
                "Team Workspaces",
                "Custom Models",
                "Priority Processing"
            ]

        if normalized == "ELITE":

            return [
                "Research",
                "Team Workspaces",
                "Priority Processing"
            ]

        if normalized == "PRO":

            return [
                "Research",
                "Reports"
            ]

        return [
            "Dashboards"
        ]
