from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.prediction_line_correction import PredictionLineCorrection
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.prediction_line_correction_service import (
    PredictionLineCorrectionService,
)
from app.services.result_settlement_service import ResultSettlementService
from app.services.v1_read_service import V1ReadService


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


@pytest.mark.parametrize(
    ("original_line", "original_outcome", "corrected_line", "corrected_outcome"),
    [
        (-30.0, "LOSS", -4.5, "WIN"),
        (-4.5, "WIN", -30.0, "LOSS"),
        (-4.5, "WIN", -26.0, "PUSH"),
    ],
)
def test_correction_audits_regrades_and_updates_performance(
    original_line,
    original_outcome,
    corrected_line,
    corrected_outcome,
):
    db = _session()
    try:
        home = Team(name="Dallas", sport="WNBA", league="WNBA")
        away = Team(name="Connecticut", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="wnba-final-1",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
            home_score=97,
            away_score=71,
            winner_team_id=home.id,
            status="final",
        )
        db.add(game)
        db.flush()
        prediction = Prediction(
            game_id=game.id,
            model_version="NPI-4.0",
            market="spread",
            selection="HOME",
            line_value=original_line,
            american_odds=-110,
            npi_score=150,
        )
        db.add(prediction)
        db.commit()

        ResultSettlementService().settle_game(db, game.id)
        before = db.query(PredictionResult).one()
        assert before.outcome == original_outcome

        correction, result = PredictionLineCorrectionService().correct_and_regrade(
            db,
            prediction_id=prediction.id,
            corrected_line=corrected_line,
            reason="Correct provider spread orientation",
            source="sportsbook reference",
        )

        assert correction.original_line == original_line
        assert correction.corrected_line == corrected_line
        assert correction.reason == "Correct provider spread orientation"
        assert correction.source == "sportsbook reference"
        assert db.query(PredictionLineCorrection).count() == 1
        assert db.query(PredictionResult).count() == 1
        assert result.outcome == corrected_outcome
        assert prediction.line_value == corrected_line

        performance = V1ReadService().get_performance(db)
        assert performance["wins"] == (1 if corrected_outcome == "WIN" else 0)
        assert performance["losses"] == (1 if corrected_outcome == "LOSS" else 0)
        assert performance["pushes"] == (1 if corrected_outcome == "PUSH" else 0)
    finally:
        db.close()