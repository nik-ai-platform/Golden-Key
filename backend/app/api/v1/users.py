from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.models.user import User

from app.core.auth_dependencies import (
    get_current_user
)

from app.schemas.user_prediction import (
    SavePredictionRequest,
    UserPredictionResponse
)

from app.services.user_prediction_service import (
    save_prediction,
    get_user_predictions
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get(
    "/me"
)
def get_profile(
    current_user: User = Depends(
        get_current_user
    )
):

    return {

        "id": current_user.id,

        "email":
        current_user.email,

        "username":
        current_user.username,

        "premium":
        current_user.is_premium

    }


@router.post(
    "/save-prediction",
    response_model=
    UserPredictionResponse
)
def save_user_prediction(
    request: SavePredictionRequest,

    current_user: User =
    Depends(get_current_user),

    db: Session =
    Depends(get_db)

):

    return save_prediction(

        db,

        current_user.id,

        request.prediction_id

    )


@router.get(
    "/my-picks",
    response_model=
    list[UserPredictionResponse]
)
def my_predictions(

    current_user: User =
    Depends(get_current_user),

    db: Session =
    Depends(get_db)

):

    return get_user_predictions(

        db,

        current_user.id

    )