from sqlalchemy import case, func

from app.models.npi_factor_result import NPIFactorResult


def save_factor_result(
    db,
    prediction_id: int,
    factor_name: str,
    weight: float,
    factor_score: float,
    predicted_side: str,
    actual_outcome: str | None = None,
):
    row = NPIFactorResult(
        prediction_id=prediction_id,
        factor_name=factor_name,
        weight=weight,
        factor_score=factor_score,
        predicted_side=predicted_side,
        actual_outcome=actual_outcome,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


class ModelEvaluation:

    def factor_summary(self, db):

        rows = (
            db.query(
                NPIFactorResult.factor_name,
                func.count(),
                func.avg(
                    NPIFactorResult.factor_score
                )
            )
            .group_by(
                NPIFactorResult.factor_name
            )
            .all()
        )

        return [
            {
                "factor": r[0],
                "games": r[1],
                "average_score": round(r[2], 2)
            }
            for r in rows
        ]

    def factor_win_rates(self, db):
        rows = (
            db.query(
                NPIFactorResult.factor_name,
                func.count(NPIFactorResult.id).label("games"),
                func.sum(
                    case(
                        (
                            NPIFactorResult.actual_outcome == NPIFactorResult.predicted_side,
                            1,
                        ),
                        else_=0,
                    )
                ).label("wins"),
            )
            .filter(NPIFactorResult.actual_outcome.is_not(None))
            .group_by(NPIFactorResult.factor_name)
            .all()
        )

        formatted = []
        for factor_name, games, wins in rows:
            if not games:
                continue
            win_rate = round((float(wins or 0) / float(games)) * 100.0, 2)
            formatted.append({"factor": factor_name, "win_rate": win_rate})
        formatted.sort(key=lambda item: item["win_rate"], reverse=True)
        return formatted