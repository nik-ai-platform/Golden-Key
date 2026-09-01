from datetime import datetime, timedelta, timezone

import pytest
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
        assert summary.finalized == 1
        assert summary.already_final == 0
        assert summary.unmatched == 0
        assert summary.skipped_not_final == 0
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
        assert summary.finalized == 0
        assert summary.already_final == 0
        assert summary.unmatched == 0
        assert summary.skipped_not_final == 1
        assert summary.settled == 0
        assert summary.errors == 0
    finally:
        db.close()


def test_previous_day_game_without_predictions_is_finalized_idempotently():
    db = _session()
    try:
        home = Team(name="Dallas", sport="WNBA", league="WNBA")
        away = Team(name="Connecticut", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="wnba-yesterday-1",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc) - timedelta(days=1),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.commit()
        provider = FakeScoreClient(
            [
                {
                    "id": "wnba-yesterday-1",
                    "completed": True,
                    "home_team": "Dallas",
                    "away_team": "Connecticut",
                    "scores": [
                        {"name": "Connecticut", "score": "71"},
                        {"name": "Dallas", "score": "97"},
                    ],
                }
            ]
        )
        service = FinalScoreSettlementService(provider_client=provider)

        first = service.sync_sport(db, "WNBA", days_from=3)
        completed_at = game.completed_at
        second = service.sync_sport(db, "WNBA", days_from=3)

        db.refresh(game)
        assert game.status == "final"
        assert game.home_score == 97
        assert game.away_score == 71
        assert game.winner_team_id == home.id
        assert completed_at is not None
        assert game.completed_at == completed_at
        assert first.finalized == 1
        assert first.already_final == 0
        assert first.settled == 0
        assert second.finalized == 0
        assert second.already_final == 1
        assert db.query(PredictionResult).count() == 0
        assert provider.calls == [
            {"sport_key": "basketball_wnba", "days_from": 3},
            {"sport_key": "basketball_wnba", "days_from": 3},
        ]
    finally:
        db.close()


def test_missed_completion_is_recovered_on_next_cycle():
    db = _session()
    try:
        home = Team(name="Home", sport="WNBA", league="WNBA")
        away = Team(name="Away", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="wnba-missed-cycle",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc) - timedelta(days=1),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.commit()
        provider = FakeScoreClient(
            [
                {
                    "id": "wnba-missed-cycle",
                    "completed": False,
                    "home_team": "Home",
                    "away_team": "Away",
                    "scores": None,
                }
            ]
        )
        service = FinalScoreSettlementService(provider_client=provider)

        first = service.sync_sport(db, "WNBA")
        provider.rows = [
            {
                "id": "wnba-missed-cycle",
                "completed": True,
                "home_team": "Home",
                "away_team": "Away",
                "scores": [
                    {"name": "Home", "score": "88"},
                    {"name": "Away", "score": "80"},
                ],
            }
        ]
        second = service.sync_sport(db, "WNBA")

        db.refresh(game)
        assert first.skipped_not_final == 1
        assert second.finalized == 1
        assert game.status == "final"
        assert (game.home_score, game.away_score) == (88, 80)
    finally:
        db.close()


def test_exact_provider_id_allows_team_alias_difference():
    db = _session()
    try:
        home = Team(name="LA Sparks", sport="WNBA", league="WNBA")
        away = Team(name="Connecticut", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="alias-event",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.commit()
        provider = FakeScoreClient(
            [{
                "id": "alias-event",
                "completed": True,
                "home_team": "Los Angeles Sparks",
                "away_team": "Connecticut Sun",
                "scores": [
                    {"name": "Connecticut Sun", "score": "71"},
                    {"name": "Los Angeles Sparks", "score": "97"},
                ],
            }]
        )

        summary = FinalScoreSettlementService(provider_client=provider).sync_sport(db, "WNBA")

        assert summary.matched == 1
        assert summary.finalized == 1
        assert summary.errors == 0
        assert (game.home_score, game.away_score) == (97, 71)
    finally:
        db.close()


def test_unmatched_provider_final_is_warned_not_errored(caplog):
    db = _session()
    try:
        provider = FakeScoreClient(
            [{
                "id": "provider-only",
                "completed": True,
                "commence_time": "2026-08-30T23:00:00Z",
                "home_team": "Portland Fire",
                "away_team": "Toronto Tempo",
                "scores": [],
            }]
        )

        summary = FinalScoreSettlementService(provider_client=provider).sync_sport(db, "WNBA")

        assert summary.unmatched == 1
        assert summary.errors == 0
        assert "provider_event_id=provider-only" in caplog.text
    finally:
        db.close()


@pytest.mark.parametrize(
    "scores",
    [
        [{"name": "Dallas Wings", "score": "97"}],
        [
            {"name": "Dallas Wings", "score": "malformed"},
            {"name": "Connecticut Sun", "score": "71"},
        ],
    ],
)
def test_invalid_completed_scores_log_context_and_traceback(caplog, scores):
    db = _session()
    try:
        home = Team(name="Dallas Wings", sport="WNBA", league="WNBA")
        away = Team(name="Connecticut Sun", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="bad-score-event",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.commit()
        provider = FakeScoreClient(
            [{
                "id": "bad-score-event",
                "completed": True,
                "status": "final",
                "home_team": "Dallas Wings",
                "away_team": "Connecticut Sun",
                "scores": scores,
            }]
        )

        summary = FinalScoreSettlementService(provider_client=provider).sync_sport(db, "WNBA")

        assert summary.matched == 1
        assert summary.errors == 1
        assert game.status == "scheduled"
        assert "local_game_id=" + str(game.id) in caplog.text
        assert "provider_status=final" in caplog.text
        assert "exception_class=ValueError" in caplog.text
        assert "Traceback" in caplog.text
    finally:
        db.close()


def test_pass_predictions_settle_without_reconciliation_errors():
    db = _session()
    try:
        home = Team(name="Seattle Storm", sport="WNBA", league="WNBA")
        away = Team(name="Los Angeles Sparks", sport="WNBA", league="WNBA")
        db.add_all([home, away])
        db.flush()
        game = Game(
            provider_game_id="pass-event",
            sport="WNBA",
            league="WNBA",
            game_date=datetime.now(timezone.utc),
            home_team_id=home.id,
            away_team_id=away.id,
        )
        db.add(game)
        db.flush()
        db.add_all([
            Prediction(
                game_id=game.id,
                market="moneyline",
                selection="PASS",
                american_odds=-115,
                npi_score=100,
            ),
            Prediction(
                game_id=game.id,
                market="total",
                selection="PASS",
                line_value=174.5,
                american_odds=-110,
                npi_score=100,
            ),
        ])
        db.commit()
        provider = FakeScoreClient(
            [{
                "id": "pass-event",
                "completed": True,
                "home_team": "Seattle Storm",
                "away_team": "Los Angeles Sparks",
                "scores": [
                    {"name": "Los Angeles Sparks", "score": "90"},
                    {"name": "Seattle Storm", "score": "74"},
                ],
            }]
        )

        summary = FinalScoreSettlementService(provider_client=provider).sync_sport(db, "WNBA")

        assert summary.errors == 0
        assert summary.settled == 1
        assert [result.outcome for result in db.query(PredictionResult).all()] == ["PUSH", "PUSH"]
    finally:
        db.close()