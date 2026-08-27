from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis


def create_analysis(
    db: Session,
    prediction_id: int,
    data: dict
):

    analysis = AIAnalysis(

        prediction_id=prediction_id,

        engine_version=
            data["engine_version"],

        summary=
            data["summary"],

        explanation=
            data["explanation"]

    )

    db.add(analysis)

    db.commit()

    db.refresh(analysis)

    return analysis
