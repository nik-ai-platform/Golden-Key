from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.persistent_user import resolve_persistent_user_id
from app.auth.schemas import AuthUser
from app.database.session import get_db
from app.schemas.api_contract import RemoveSavedPredictionResponse
from app.schemas.user_prediction import (
    SavePredictionRequest,
    UserPredictionResponse,
)
from app.services.user_prediction_service import (
    get_user_predictions,
    remove_saved_prediction,
    save_prediction,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me")
def get_profile(
    current_user: AuthUser = Depends(get_current_user),
):
    return current_user


@router.post(
    "/save-prediction",
    response_model=UserPredictionResponse,
)
def save_user_prediction(
    request: SavePredictionRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_persistent_user_id(
        db,
        current_user,
    )

    return save_prediction(
        db,
        user_id,
        request.prediction_id,
    )


@router.delete(
    "/saved-predictions/{prediction_id}",
    response_model=RemoveSavedPredictionResponse,
)
def remove_user_prediction(
    prediction_id: int,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_persistent_user_id(
        db,
        current_user,
    )
    removed = remove_saved_prediction(
        db,
        user_id,
        prediction_id,
    )
    return {
        "removed": removed,
        "prediction_id": prediction_id,
    }


@router.get(
    "/my-picks",
    response_model=list[UserPredictionResponse],
)
def my_predictions(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = resolve_persistent_user_id(
        db,
        current_user,
    )

    return get_user_predictions(
        db,
        user_id,
    )