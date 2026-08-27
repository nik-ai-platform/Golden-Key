from sqlalchemy.orm import Session

from app.models.model_version import ModelVersion
from app.models.model_registry import ModelRegistry
from app.models.backtest_result import BacktestResult


class ModelPromotionService:

    MIN_GAMES = 500
    MIN_ATS_WIN_RATE = 52.38

    def evaluate_candidate(
        self,
        db: Session,
        model_version: str,
        sport: str,
    ):
        results = (
            db.query(BacktestResult)
            .filter(
                BacktestResult.model_version == model_version,
                BacktestResult.sport == sport,
            )
            .all()
        )

        total_games = len(results)

        if total_games == 0:
            return {
                "eligible": False,
                "reason": "No backtest results found",
                "games": 0,
                "ats_win_rate": 0.0,
            }

        ats_results = [
            result
            for result in results
            if result.market == "spread" and result.outcome in {"WIN", "LOSS"}
        ]

        ats_total = len(ats_results)

        ats_wins = sum(1 for result in ats_results if result.outcome == "WIN")

        ats_win_rate = ((ats_wins / ats_total) * 100 if ats_total else 0.0)

        if total_games < self.MIN_GAMES:
            return {
                "eligible": False,
                "reason": f"Minimum {self.MIN_GAMES} games required",
                "games": total_games,
                "ats_win_rate": round(ats_win_rate, 2),
            }

        if ats_win_rate < self.MIN_ATS_WIN_RATE:
            return {
                "eligible": False,
                "reason": "ATS win rate below " f"{self.MIN_ATS_WIN_RATE}%",
                "games": total_games,
                "ats_win_rate": round(ats_win_rate, 2),
            }

        return {
            "eligible": True,
            "reason": "Candidate meets promotion requirements",
            "games": total_games,
            "ats_win_rate": round(ats_win_rate, 2),
        }

    def promote(
        self,
        db: Session,
        model_version: str,
        sport: str,
        approved_by: str | None = None,
        notes: str | None = None,
    ):
        evaluation = self.evaluate_candidate(
            db=db,
            model_version=model_version,
            sport=sport,
        )

        if not evaluation["eligible"]:
            return {
                "promoted": False,
                "status": "rejected",
                "evaluation": evaluation,
            }

        if not approved_by:
            return {
                "promoted": False,
                "status": "pending_approval",
                "evaluation": evaluation,
            }

        model_record = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.version == model_version,
                ModelVersion.sport == sport,
            )
            .first()
        )

        if not model_record:
            model_record = ModelVersion(
                model_name=f"{sport}_model",
                version=model_version,
                sport=sport,
            )

            db.add(model_record)

        current_registry_entry = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.sport == sport,
                ModelRegistry.is_active.is_(True),
            )
            .first()
        )

        if current_registry_entry:
            current_registry_entry.is_active = False
            current_registry_entry.production_status = False

        registry_entry = (
            db.query(ModelRegistry)
            .filter(
                ModelRegistry.model_version == model_version,
                ModelRegistry.sport == sport,
            )
            .first()
        )

        if not registry_entry:
            registry_entry = ModelRegistry(
                model_name=model_record.model_name,
                model_version=model_version,
                sport=sport,
                version=model_version,
            )

            db.add(registry_entry)

        registry_entry.is_active = True
        registry_entry.production_status = True

        model_record.status = "production"
        model_record.ats_accuracy = evaluation["ats_win_rate"]
        model_record.games_evaluated = evaluation["games"]
        model_record.approved_by = approved_by
        model_record.notes = notes

        db.commit()

        db.refresh(model_record)
        db.refresh(registry_entry)

        return {
            "promoted": True,
            "status": "production",
            "model_version": model_version,
            "sport": sport,
            "evaluation": evaluation,
            "approved_by": approved_by,
        }
