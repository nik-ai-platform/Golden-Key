from sqlalchemy.orm import Session
from datetime import datetime, timezone
from uuid import uuid4

from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.schemas.prediction import PredictionCreate
from app.services.ncaaf_rule_intelligence_service import (
    record_rule_intelligence_for_prediction,
)
from app.services.prediction_revision import input_fingerprint as fingerprint_payload


def create_prediction(
    db: Session,
    prediction: PredictionCreate,
    *,
    commit: bool = True,
    generation_id: str | None = None,
    input_fingerprint: str | None = None,
):
    if (generation_id is None) != (input_fingerprint is None):
        raise ValueError("Prediction revision identity and fingerprint must be supplied together")
    if generation_id is None:
        # Standalone/API writes share the engine/settlement lock and compare only
        # the current publication, so reverting inputs does not revive history.
        game = db.query(Game).filter(Game.id == prediction.game_id).populate_existing().with_for_update().first()
        if game is None:
            raise ValueError("Game not found")
        input_fingerprint = fingerprint_payload({
            "contract": "manual-publication-v1", "publication": prediction.model_dump(),
        })
        existing = (
            db.query(Prediction)
            .filter(
                Prediction.game_id == prediction.game_id,
                Prediction.model_version == prediction.model_version,
                Prediction.market == prediction.market,
            ).order_by(Prediction.id.desc()).populate_existing().first()
        )
        if existing is not None and existing.input_fingerprint == input_fingerprint:
            if commit:
                db.commit()
            return existing
        settled = (
            db.query(PredictionResult.id)
            .join(Prediction, Prediction.id == PredictionResult.prediction_id)
            .filter(Prediction.game_id == game.id).first()
        )
        if (
            game.status == "final" or settled is not None
            or game.game_date <= datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            db.rollback()
            raise ValueError("Cannot publish a revision for a started, final, or settled game")
        generation_id = str(uuid4())
    db_prediction = Prediction(
        **prediction.model_dump(),
        generation_id=generation_id,
        input_fingerprint=input_fingerprint,
    )

    db.add(db_prediction)
    db.flush()
    odds_snapshot = (
        db.get(Odds, db_prediction.odds_snapshot_id)
        if db_prediction.odds_snapshot_id is not None
        else None
    )
    record_rule_intelligence_for_prediction(
        db=db,
        prediction=db_prediction,
        odds_snapshot=odds_snapshot,
    )
    if commit:
        db.commit()
        db.refresh(db_prediction)

    return db_prediction


def get_predictions(
    db: Session,
):
    return (
        db.query(Prediction)
        .order_by(Prediction.created_at.desc())
        .all()
    )
