from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.subscription import Subscription


def require_premium(
    user,
    db: Session
):

    subscription = (

        db.query(Subscription)

        .filter(
            Subscription.user_id ==
            user.id
        )

        .first()

    )

    if not subscription:

        raise HTTPException(
            status_code=403,
            detail="Premium required"
        )

    if subscription.plan != "premium":

        raise HTTPException(
            status_code=403,
            detail="Premium required"
        )

    return True