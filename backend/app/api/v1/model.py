from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.model_version import ModelVersion
from app.services.model_evaluation import ModelEvaluation


router = APIRouter(
    prefix="/model",
    tags=["Model Evaluation"],
)

evaluation = ModelEvaluation()


@router.get("/factors")
def model_factors(
    db: Session = Depends(get_db)
):
    latest = (
        db.query(ModelVersion)
        .order_by(ModelVersion.created_at.desc(), ModelVersion.id.desc())
        .first()
    )

    top_factors = evaluation.factor_win_rates(db)

    if not top_factors:
        top_factors = [
            {
                "factor": item["factor"],
                "win_rate": 0,
            }
            for item in evaluation.factor_summary(db)
        ]

    return {
        "version": latest.version if latest else "NPI-4.0",
        "overall_accuracy": float(latest.overall_accuracy or 0) if latest else 0,
        "ats_accuracy": float(latest.ats_accuracy or 0) if latest else 0,
        "top_factors": top_factors[:5],
    }