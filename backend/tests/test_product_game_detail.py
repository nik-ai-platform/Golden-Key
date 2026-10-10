from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.npi_factor_result import NPIFactorResult
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.v1_read_service import V1ReadService


def test_game_detail_exposes_authoritative_scores_and_results():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    home = Team(name="Seattle Seahawks", league="NFL", sport="NFL")
    away = Team(name="New England Patriots", league="NFL", sport="NFL")
    db.add_all([home, away])
    db.flush()
    game = Game(
        sport="NFL",
        league="NFL",
        game_date=datetime(2026, 9, 10, 0, 15),
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=24,
        away_score=21,
    )
    db.add(game)
    db.flush()
    odds = Odds(
        game_id=game.id,
        sportsbook="DraftKings",
        spread_home=-3.5,
        spread_away=3.5,
        spread_home_price=-110,
        spread_away_price=-110,
        moneyline_home=-165,
        moneyline_away=145,
        total=44.5,
        total_over_price=-110,
        total_under_price=-110,
        created_at=datetime(2026, 9, 10, 0, 10),
    )
    db.add(odds)
    db.flush()
    predictions = []
    for index, market in enumerate(("spread", "moneyline", "total")):
        prediction = Prediction(
            game_id=game.id,
            market=market,
            selection="OVER" if market == "total" else "HOME",
            line_value=(
                -3.5
                if market == "spread"
                else 44.5 if market == "total" else None
            ),
            american_odds=-110,
            odds_snapshot_id=odds.id if index == 0 else None,
            sportsbook="DraftKings" if index == 0 else None,
            odds_observed_at=odds.created_at if index == 0 else None,
            npi_score=150,
            confidence_score=80,
            model_version="NPI-4.0",
            reasoning="Spread model. Key Advantages: Recorded home rule.",
        )
        db.add(prediction)
        db.flush()
        predictions.append(prediction)
    db.add(
        NPIFactorResult(
            prediction_id=predictions[0].id,
            factor_name="Home Advantage",
            weight=20,
            factor_score=20,
            predicted_side="HOME",
            created_at=datetime(2026, 9, 10, 0, 11),
        )
    )
    db.add(
        NPIFactorResult(
            prediction_id=predictions[0].id,
            factor_name="Historical Rule Engine",
            weight=80,
            factor_score=20,
            predicted_side="HOME",
            created_at=datetime(2026, 9, 10, 0, 11),
        )
    )
    for prediction, outcome in zip(
        predictions,
        ("WIN", "LOSS", "PUSH"),
        strict=True,
    ):
        db.add(
            PredictionResult(
                prediction_id=prediction.id,
                actual_result="HOME",
                predicted_result="HOME",
                outcome=outcome,
                profit_loss=0,
            )
        )
    db.commit()

    detail = V1ReadService().get_game_detail(db=db, game_id=game.id)

    assert detail["game_date"] == "2026-09-10T00:15:00Z"
    assert detail["home_score"] == 24
    assert detail["away_score"] == 21
    assert [prediction["outcome"] for prediction in detail["predictions"]] == [
        "WIN",
        "LOSS",
        "PUSH",
    ]
    spread_detail = detail["predictions"][0]
    assert spread_detail["signal_breakdown"]["model_version"] == "NPI-4.0"
    assert spread_detail["signal_breakdown"]["prediction_recorded_at"] is not None
    assert [factor["factor_name"] for factor in spread_detail["signal_breakdown"]["factors"]] == [
        "Home Advantage",
        "Historical Rule Engine",
    ]
    assert spread_detail["signal_breakdown"]["factors"][0]["factor_score"] == 20
    assert spread_detail["signal_breakdown"]["factors"][0]["predicted_side"] == "HOME"
    assert spread_detail["signal_breakdown"]["frozen_odds"]["snapshot_id"] == odds.id
    assert spread_detail["signal_breakdown"]["frozen_odds"]["spread_home"] == -3.5
    assert detail["predictions"][1]["signal_breakdown"] is None
    db.close()