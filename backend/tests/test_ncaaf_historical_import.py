from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models.game import Game
from app.models.game_provider_identity import GameProviderIdentity
from app.models.game_result_observation import GameResultObservation
from app.models.import_run import ImportRun
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.team_alias import TeamAlias
from app.models.team_provider_identity import TeamProviderIdentity
from app.models.team_season import TeamSeason
from app.providers.cfbd_dtos import CFBDGame, CFBDTeam, CFBDTeamSeason
from app.services.ncaaf_historical_results_import_service import (
    NCAAFHistoricalResultsImportService,
)


class FakeCFBDClient:
    def __init__(self):
        self.score_revision = 0

    def get_teams(self, season):
        return [
            CFBDTeam(1, "Home State", ("Home St.",), "HST"),
            CFBDTeam(2, "Away Tech", ("Away Institute",), "AT"),
        ]

    def get_team_metadata(self, season):
        return [
            CFBDTeamSeason(1, "Home State", "Alpha", "FBS", "I-A", True),
            CFBDTeamSeason(2, "Away Tech", None, None, None, None),
        ]

    def get_games(self, season):
        kickoff = datetime(season, 9, 6, 19, 30)
        source_updated_at = datetime(season, 9, 7, 2, 0) if season == 2026 else None
        return [
            CFBDGame(
                id=season * 10 + 1,
                season=season,
                start_date=kickoff,
                home_id=1,
                away_id=2,
                home_team="Home State",
                away_team="Away Tech",
                home_points=31 + self.score_revision,
                away_points=20,
                completed=True,
                neutral_site=True,
                venue_name="History Field",
                venue_city="Town",
                venue_state="TX",
                source_updated_at=source_updated_at,
            ),
            CFBDGame(
                id=season * 10 + 2,
                season=season,
                start_date=kickoff + timedelta(days=7),
                home_id=2,
                away_id=1,
                home_team="Away Tech",
                away_team="Home State",
                home_points=None,
                away_points=None,
                completed=False,
                neutral_site=False,
                venue_name=None,
                venue_city=None,
                venue_state=None,
            ),
            CFBDGame(
                id=season * 10 + 3,
                season=season,
                start_date=kickoff + timedelta(days=14),
                home_id=1,
                away_id=2,
                home_team="Home State",
                away_team="Away Tech",
                home_points=None,
                away_points=None,
                completed=False,
                neutral_site=None,
                venue_name=None,
                venue_city=None,
                venue_state=None,
            ),
        ]


class ScopedCFBDClient:
    def get_teams(self, season):
        return [
            CFBDTeam(1, "FBS School"),
            CFBDTeam(2, "FCS School"),
            CFBDTeam(3, "Division Two"),
            CFBDTeam(4, "Lower School"),
        ]

    def get_team_metadata(self, season):
        return [
            CFBDTeamSeason(1, "FBS School", "A", "FBS", "I-A", True),
            CFBDTeamSeason(2, "FCS School", "B", "FCS", "I-AA", False),
            CFBDTeamSeason(3, "Division Two", "C", "II", "II", False),
            CFBDTeamSeason(4, "Lower School", "D", "III", "III", False),
        ]

    def get_games(self, season):
        kickoff = datetime(season, 9, 1, 12, 0)
        return [
            _game(season * 10 + 1, season, kickoff, 1, "FBS School", 5, "Game Only"),
            _game(season * 10 + 2, season, kickoff, 2, "FCS School", 3, "Division Two"),
            _game(season * 10 + 3, season, kickoff, 3, "Division Two", 4, "Lower School"),
        ]


def _game(game_id, season, kickoff, home_id, home_team, away_id, away_team):
    return CFBDGame(
        id=game_id,
        season=season,
        start_date=kickoff,
        home_id=home_id,
        away_id=away_id,
        home_team=home_team,
        away_team=away_team,
        home_points=20,
        away_points=10,
        completed=True,
        neutral_site=False,
        venue_name=None,
        venue_city=None,
        venue_state=None,
    )


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_dry_run_rolls_back_every_mutation(db):
    report = NCAAFHistoricalResultsImportService(db, FakeCFBDClient()).import_seasons(
        [2025],
        dry_run=True,
    )

    assert report.games_created == 3
    assert report.observations_created == 1
    assert db.query(Team).count() == 0
    assert db.query(Game).count() == 0
    assert db.query(ImportRun).count() == 0


def test_apply_is_idempotent_and_preserves_season_metadata(db):
    client = FakeCFBDClient()
    service = NCAAFHistoricalResultsImportService(db, client)
    first = service.import_seasons([2025, 2026], dry_run=False)
    second = service.import_seasons([2025, 2026], dry_run=False)

    assert first.games_created == 6
    assert second.games_created == 0
    assert second.observations_created == 0
    assert second.aliases_created == 0
    assert second.team_seasons_updated == 0
    assert db.query(Team).count() == 2
    assert db.query(TeamProviderIdentity).count() == 2
    assert db.query(TeamAlias).count() == 6
    assert db.query(TeamSeason).count() == 4
    assert {row.season for row in db.query(TeamSeason).all()} == {2025, 2026}
    assert db.query(Game).count() == 6
    assert db.query(GameResultObservation).count() == 2

    games = db.query(Game).filter(Game.season == 2025).order_by(Game.game_date).all()
    assert [game.neutral_site for game in games] == [True, False, None]
    assert games[0].historical_result_observed_at == games[0].game_date + timedelta(hours=6)
    game_2026 = (
        db.query(Game)
        .filter(Game.season == 2026, Game.status == "final")
        .one()
    )
    assert game_2026.historical_result_observed_at == datetime(2026, 9, 7, 2, 0)


def test_changed_result_creates_append_only_observation(db):
    client = FakeCFBDClient()
    service = NCAAFHistoricalResultsImportService(db, client)
    service.import_seasons([2025], dry_run=False)
    original = db.query(GameResultObservation).one()

    client.score_revision = 1
    report = service.import_seasons([2025], dry_run=False)
    observations = db.query(GameResultObservation).order_by(GameResultObservation.id).all()

    assert report.observations_created == 1
    assert len(observations) == 2
    assert observations[0].home_score == original.home_score == 31
    assert observations[1].home_score == 32
    assert observations[0].payload_hash != observations[1].payload_hash


def test_reconciliation_preserves_legacy_ids_and_prediction_records(db):
    home = Team(name="Home State", league="NCAAF", sport="NCAAF")
    away = Team(name="Away Tech", league="NCAAF", sport="NCAAF")
    db.add_all([home, away])
    db.flush()
    kickoff = datetime(2025, 9, 6, 17, 30)
    existing_game = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2025,
        provider_game_id="odds-event-1",
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=kickoff,
        home_score=10,
        away_score=7,
        status="final",
        neutral_site=None,
        venue_name="Known Venue",
    )
    db.add(existing_game)
    db.flush()
    odds = Odds(game_id=existing_game.id, sportsbook="Book", spread_home=-3)
    db.add(odds)
    db.flush()
    prediction = Prediction(
        game_id=existing_game.id,
        market="spread",
        selection="home",
        npi_score=0.6,
        odds_snapshot_id=odds.id,
    )
    db.add(prediction)
    db.flush()
    result = PredictionResult(
        prediction_id=prediction.id,
        actual_result="win",
        predicted_result="win",
        outcome="win",
    )
    db.add(result)
    db.commit()

    before = {
        "odds": db.query(Odds).count(),
        "predictions": db.query(Prediction).count(),
        "results": db.query(PredictionResult).count(),
    }
    report = NCAAFHistoricalResultsImportService(db, FakeCFBDClient()).import_seasons(
        [2025],
        dry_run=False,
    )
    db.refresh(existing_game)

    assert report.games_matched == 1
    assert existing_game.provider_game_id == "odds-event-1"
    assert (existing_game.home_score, existing_game.away_score) == (10, 7)
    assert existing_game.status == "final"
    assert existing_game.neutral_site is True
    assert existing_game.venue_name == "History Field"
    odds_identity = (
        db.query(GameProviderIdentity)
        .filter(GameProviderIdentity.provider == "the_odds_api")
        .one()
    )
    cfbd_identity = (
        db.query(GameProviderIdentity)
        .filter(GameProviderIdentity.provider == "cfbd")
        .first()
    )
    assert odds_identity.game_id == existing_game.id
    assert odds_identity.provider_game_id == "odds-event-1"
    assert cfbd_identity.game_id == existing_game.id
    assert before == {
        "odds": db.query(Odds).count(),
        "predictions": db.query(Prediction).count(),
        "results": db.query(PredictionResult).count(),
    }


def test_ambiguous_team_mapping_is_quarantined(db):
    db.add_all(
        [
            Team(name="Home State", league="NCAAF", sport="NCAAF"),
            Team(name="Home-State", league="NCAAF", sport="NCAAF"),
        ]
    )
    db.commit()

    report = NCAAFHistoricalResultsImportService(db, FakeCFBDClient()).import_seasons(
        [2025],
        dry_run=False,
    )

    assert report.ambiguous_records >= 1
    assert all(
        identity.provider_team_id != "1"
        for identity in db.query(TeamProviderIdentity).all()
    )
    assert db.query(Game).count() == 0


def test_scope_includes_fbs_fcs_support_and_game_only_teams(db):
    report = NCAAFHistoricalResultsImportService(db, ScopedCFBDClient()).import_seasons(
        [2025],
        dry_run=False,
    )

    assert report.provider_games_fetched == 3
    assert report.relevant_games == 2
    assert report.excluded_games == 1
    assert report.excluded_game_classifications == {"II vs III": 1}
    assert report.game_only_teams_proposed == 1
    assert report.games_created == 2
    assert db.query(Team).count() == 4
    game_only_identity = (
        db.query(TeamProviderIdentity)
        .filter(TeamProviderIdentity.provider_team_id == "5")
        .one()
    )
    assert db.get(Team, game_only_identity.team_id).name == "Game Only"
    assert (
        db.query(TeamSeason)
        .filter(TeamSeason.team_id == game_only_identity.team_id)
        .count()
        == 0
    )


def test_report_counts_resolution_methods_and_timestamp_provenance(db):
    report = NCAAFHistoricalResultsImportService(db, FakeCFBDClient()).import_seasons(
        [2025, 2026],
        dry_run=False,
    )

    assert report.match_method_counts == {"new_team": 2, "provider_identity": 2}
    assert report.fallback_timestamp_observations == 1
    assert report.provider_timestamp_observations == 1