from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.database.session import get_db

from app.schemas.subscription import (
    SubscriptionResponse
)

from app.services.subscription_service import (
    get_user_subscription
)

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)


@router.get(
    "/me",
    response_model=
    SubscriptionResponse
)
def my_subscription(

    current_user: AuthUser =
        Depends(get_current_user),

    db: Session =
        Depends(get_db)

):

    return get_user_subscription(
        db,
        current_user.id
    )