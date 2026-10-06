from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.backtest_result import BacktestResult
from app.models.game import Game
from app.models.model_version import ModelVersion
from app.services.model_evaluation import ModelEvaluation
from app.models.nik_score import NikScore
from app.services.performance_scope import regular_backtest_history, regular_model_metrics


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
    metrics = (
        regular_model_metrics(db).filter(
            NikScore.model_version == latest.version,
            Game.sport == latest.sport,
        ).first()
        if latest else None
    )
    backtest = (
        regular_backtest_history(db.query(
            func.count(BacktestResult.id).label("games"),
            func.sum(case(
                (func.upper(BacktestResult.win_loss) == "WIN", 1),
                else_=0,
            )).label("wins"),
        )).filter(
            BacktestResult.backtest_id.is_not(None),
            BacktestResult.model_version == latest.version,
            Game.sport == latest.sport,
        ).one()
    ) if latest else None

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
        "overall_accuracy": float(metrics.accuracy or 0) if metrics else 0,
        "ats_accuracy": (
            round(float(backtest.wins or 0) / backtest.games * 100, 2)
            if backtest and backtest.games else 0
        ),
        "top_factors": top_factors[:5],
    }