from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.services.final_score_settlement_service import (
    FinalScoreSettlementService,
)


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


class FakeScoreClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get_scores(self, sport_key, *, days_from=3):
        self.calls.append(
            {
                "sport_key": sport_key,
                "days_from": days_from,
            }
        )
        return self.rows


def test_sync_sport_updates_scores_and_settles_predictions():
    db = _session()

    try:
        home = Team(
            name="Rutgers Scarlet Knights",
            sport="NCAAF",
            league="NCAAF",
        )
        away = Team(
            name="UMass Minutemen",
            sport="NCAAF",
            league="NCAAF",
        )
        db.add_all([home, away])
        db.flush()

        game = Game(
            provider_game_id="provider-1",
            sport="NCAAF",
            league="NCAAF",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.flush()

        prediction = Prediction(
            game_id=game.id,
            market="spread",
            selection="HOME",
            line_value=-6.5,
            american_odds=-110,
            npi_score=150.0,
            win_probability=60.0,
            projected_edge=7.6,
            confidence_score=80.0,
            risk_level="LOW",
            model_version="NPI-4.0",
        )
        db.add(prediction)
        db.commit()

        provider = FakeScoreClient(
            [
                {
                    "id": "provider-1",
                    "completed": True,
                    "home_team": "Rutgers Scarlet Knights",
                    "away_team": "UMass Minutemen",
                    "scores": [
                        {
                            "name": "Rutgers Scarlet Knights",
                            "score": "31",
                        },
                        {
                            "name": "UMass Minutemen",
                            "score": "21",
                        },
                    ],
                }
            ]
        )

        summary = FinalScoreSettlementService(
            provider_client=provider,
        ).sync_sport(
            db,
            "NCAAF",
        )

        db.refresh(game)
        assert provider.calls == [
            {
                "sport_key": "americanfootball_ncaaf",
                "days_from": 3,
            }
        ]
        assert game.home_score == 31
        assert game.away_score == 21
        assert game.winner_team_id == home.id

        result = (
            db.query(PredictionResult)
            .filter(PredictionResult.prediction_id == prediction.id)
            .one()
        )
        assert result.outcome == "WIN"
        assert summary.fetched == 1
        assert summary.matched == 1
        assert summary.updated == 1
        assert summary.settled == 1
        assert summary.errors == 0
    finally:
        db.close()


def test_sync_sport_ignores_uncompleted_games():
    db = _session()

    try:
        provider = FakeScoreClient(
            [
                {
                    "id": "provider-2",
                    "completed": False,
                    "home_team": "Team A",
                    "away_team": "Team B",
                    "scores": None,
                }
            ]
        )

        summary = FinalScoreSettlementService(
            provider_client=provider,
        ).sync_sport(
            db,
            "NCAAF",
        )

        assert summary.fetched == 1
        assert summary.matched == 0
        assert summary.updated == 0
        assert summary.settled == 0
        assert summary.skipped == 1
        assert summary.errors == 0
    finally:
        db.close()