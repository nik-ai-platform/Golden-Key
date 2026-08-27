from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.prediction_result import (
    PredictionResultCreate,
    PredictionResultResponse
)

from app.services.result_service import (
    record_result,
    get_results
)

router = APIRouter(
    prefix="/results",
    tags=["Results"]
)


@router.post(
    "/",
    response_model=PredictionResultResponse
)
def create_result(
    result: PredictionResultCreate,
    db: Session = Depends(get_db)
):

    return record_result(
        db,
        result
    )


@router.get(
    "/",
    response_model=list[PredictionResultResponse]
)
def results(
    db: Session = Depends(get_db)
):

    return get_results(
        db
    )