from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import AuthUser
from app.database.session import get_db

from app.core.premium import (
    require_premium
)

router = APIRouter(
    prefix="/premium",
    tags=["Premium"]
)


@router.get(
    "/advanced-analysis"
)
def advanced_analysis(

    current_user: AuthUser =
        Depends(get_current_user),

    db: Session =
        Depends(get_db)

):

    require_premium(
        current_user,
        db
    )

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