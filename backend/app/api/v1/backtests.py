from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_analyst
from app.database.session import get_db
from app.schemas.backtest import BacktestRequest
from app.services.backtest_engine import BacktestEngine


router = APIRouter(
    prefix="/backtests",
    tags=["Backtests"],
    dependencies=[Depends(require_analyst)],
)


engine = BacktestEngine()


@router.post("/run")
def run_backtest(payload: BacktestRequest, db: Session = Depends(get_db)):
    outcome = engine.run(
        db=db,
        model_version=payload.model_version,
        start_date=payload.start_date,
        end_date=payload.end_date,
        sport=payload.sport,
        market=payload.market,
    )

    stats = outcome["stats"]
    return {
        "id": outcome["backtest_id"],
        "model": outcome["model_version"],
        "sport": outcome["sport"],
        "start_date": outcome["start_date"].isoformat(),
        "end_date": outcome["end_date"].isoformat(),
        "games": stats["games_tested"],
        "accuracy": stats["win_pct"],
        "ats_record": stats["ats_record"],
        "roi": stats["roi"],
        "calibration_error": 0.0,
        "recommendation": "promote" if stats["roi"] > 0 and stats["win_pct"] >= 55 else "hold",
        "stats": stats,
    }


@router.get("")
def list_backtests(db: Session = Depends(get_db)):
    runs = engine.run_summaries(db)
    return {
        "runs": runs,
        "version_comparison": engine.version_comparison(db),
    }


@router.get("/{backtest_id}")
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    summary = engine.run_summary(db, backtest_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return summary
