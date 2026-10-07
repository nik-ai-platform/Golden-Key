from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.premium import require_premium_user
from app.auth.schemas import AuthUser
from app.database.session import get_db

router = APIRouter(
    prefix="/premium",
    tags=["Premium"]
)


@router.get(
    "/advanced-analysis"
)
def advanced_analysis(

    current_user: AuthUser =
        Depends(require_premium_user),

    db: Session =
        Depends(get_db)

):

    return {

        "message":
        "Premium AI analytics unlocked",

        "features":[

            "Advanced NPI breakdown",

            "Simulation history",

            "Model confidence trends",

            "Sharp money tracking"

        ]

    }