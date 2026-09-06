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
from app.data.ncaaf_game_reconciliation import (
    REVIEWED_CFBD_GAME_MAPPINGS,
    ReviewedGameMapping,
)
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
            _game(season * 10 + 1, season, kickoff, 1, "FBS School", 5005, "Game Only"),
            _game(season * 10 + 2, season, kickoff, 2, "FCS School", 3, "Division Two"),
            _game(season * 10 + 3, season, kickoff, 3, "Division Two", 4, "Lower School"),
        ]


class SingleGameCFBDClient(FakeCFBDClient):
    def get_games(self, season):
        return super().get_games(season)[:1]


class FutureOnlyCFBDClient(FakeCFBDClient):
    def get_games(self, season):
        return super().get_games(season)[1:2]


class UnknownNeutralCFBDClient(FakeCFBDClient):
    def get_games(self, season):
        game = super().get_games(season)[0]
        return [
            CFBDGame(
                id=game.id,
                season=game.season,
                start_date=game.start_date,
                home_id=game.home_id,
                away_id=game.away_id,
                home_team=game.home_team,
                away_team=game.away_team,
                home_points=game.home_points,
                away_points=game.away_points,
                completed=True,
                neutral_site=None,
                venue_name=game.venue_name,
                venue_city=game.venue_city,
                venue_state=game.venue_state,
            )
        ]


class DuplicateGameCFBDClient(FakeCFBDClient):
    def get_games(self, season):
        first = super().get_games(season)[0]
        return [
            first,
            CFBDGame(
                id=season * 10 + 4,
                season=season,
                start_date=first.start_date + timedelta(hours=20),
                home_id=first.home_id,
                away_id=first.away_id,
                home_team=first.home_team,
                away_team=first.away_team,
                home_points=28,
                away_points=19,
                completed=True,
                neutral_site=False,
                venue_name="History Field",
                venue_city="Town",
                venue_state="TX",
            ),
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
        completed_only=True,
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
        completed_only=True,
    )

    assert report.ambiguous_records >= 1
    assert report.ambiguities >= 1
    assert report.completed_observations_proposed == 0
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
        .filter(TeamProviderIdentity.provider_team_id == "5005")
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
    observations = {
        db.get(Game, observation.game_id).season: observation
        for observation in db.query(GameResultObservation).all()
    }
    assert observations[2025].source_updated_at is None
    assert observations[2025].observed_at == datetime(2025, 9, 7, 1, 30)
    assert observations[2026].source_updated_at == datetime(2026, 9, 7, 2, 0)
    assert observations[2026].observed_at == datetime(2026, 9, 7, 2, 0)


def test_reviewed_game_mapping_precedes_time_window_and_preserves_legacy_id(db):
    home = Team(name="Home State", league="NCAAF", sport="NCAAF")
    away = Team(name="Away Tech", league="NCAAF", sport="NCAAF")
    db.add_all([home, away])
    db.flush()
    existing = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2025,
        provider_game_id="odds-reviewed",
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime(2025, 9, 6, 7, 30),
        status="final",
    )
    db.add(existing)
    db.commit()
    REVIEWED_CFBD_GAME_MAPPINGS["20251"] = ReviewedGameMapping(
        existing.id,
        "test evidence",
    )
    try:
        report = NCAAFHistoricalResultsImportService(
            db,
            SingleGameCFBDClient(),
        ).import_seasons([2025], dry_run=False, completed_only=True)
    finally:
        REVIEWED_CFBD_GAME_MAPPINGS.pop("20251")

    assert report.reviewed_game_matches == 1
    assert report.games_matched == 1
    assert report.games_created == 0
    assert db.query(Game).count() == 1
    assert existing.provider_game_id == "odds-reviewed"
    cfbd_identity = (
        db.query(GameProviderIdentity)
        .filter(GameProviderIdentity.provider == "cfbd")
        .one()
    )
    assert cfbd_identity.game_id == existing.id


def test_unreviewed_kickoff_conflict_is_quarantined(db):
    home = Team(name="Home State", league="NCAAF", sport="NCAAF")
    away = Team(name="Away Tech", league="NCAAF", sport="NCAAF")
    db.add_all([home, away])
    db.flush()
    db.add(
        Game(
            sport="NCAAF",
            league="NCAAF",
            season=2025,
            provider_game_id="odds-conflict",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2025, 9, 6, 7, 30),
            status="final",
        )
    )
    db.commit()

    report = NCAAFHistoricalResultsImportService(
        db,
        SingleGameCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    assert report.quarantined_games == 1
    assert report.games_created == 0
    assert db.query(Game).count() == 1
    assert db.query(GameResultObservation).count() == 0
    assert not db.query(GameProviderIdentity).filter(
        GameProviderIdentity.provider == "cfbd"
    ).count()


def test_same_team_rematch_outside_review_window_stays_distinct(db):
    home = Team(name="Home State", league="NCAAF", sport="NCAAF")
    away = Team(name="Away Tech", league="NCAAF", sport="NCAAF")
    db.add_all([home, away])
    db.flush()
    db.add(
        Game(
            sport="NCAAF",
            league="NCAAF",
            season=2025,
            provider_game_id="odds-rematch",
            home_team_id=home.id,
            away_team_id=away.id,
            game_date=datetime(2025, 9, 20, 19, 30),
            status="scheduled",
        )
    )
    db.commit()

    report = NCAAFHistoricalResultsImportService(
        db,
        SingleGameCFBDClient(),
    ).import_seasons([2025], dry_run=False)

    assert report.quarantined_games == 0
    assert report.games_created == 1
    assert db.query(Game).count() == 2


def test_provider_duplicate_risk_quarantines_both_records(db):
    report = NCAAFHistoricalResultsImportService(
        db,
        DuplicateGameCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    assert report.provider_duplicate_risk_games == 2
    assert report.quarantined_games == 2
    assert report.games_created == 0
    assert report.observations_created == 0
    assert db.query(Game).count() == 0


def test_completed_only_skips_unmatched_future_without_side_effects(db):
    report = NCAAFHistoricalResultsImportService(
        db,
        FutureOnlyCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    assert report.future_cfbd_only_skipped == 1
    assert report.future_cfbd_only_games_created == 0
    assert report.teams_proposed_create == 0
    assert db.query(Team).count() == 0
    assert db.query(Game).count() == 0
    assert db.query(GameProviderIdentity).count() == 0
    assert db.query(GameResultObservation).count() == 0


def test_completed_only_reuses_existing_future_game(db):
    home = Team(name="Away Tech", league="NCAAF", sport="NCAAF")
    away = Team(name="Home State", league="NCAAF", sport="NCAAF")
    db.add_all([home, away])
    db.flush()
    existing = Game(
        sport="NCAAF",
        league="NCAAF",
        season=2025,
        provider_game_id="odds-future",
        home_team_id=home.id,
        away_team_id=away.id,
        game_date=datetime(2025, 9, 13, 19, 30),
        status="scheduled",
    )
    db.add(existing)
    db.commit()

    report = NCAAFHistoricalResultsImportService(
        db,
        FutureOnlyCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    assert report.future_existing_matches == 1
    assert report.future_cfbd_only_skipped == 0
    assert report.future_cfbd_only_games_created == 0
    assert db.query(Game).count() == 1
    assert existing.provider_game_id == "odds-future"
    assert db.query(GameProviderIdentity).filter(
        GameProviderIdentity.provider == "cfbd",
        GameProviderIdentity.game_id == existing.id,
    ).count() == 1
    assert db.query(GameResultObservation).count() == 0


def test_completed_only_creates_scored_game_with_known_neutral_status(db):
    report = NCAAFHistoricalResultsImportService(
        db,
        SingleGameCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    game = db.query(Game).one()
    observation = db.query(GameResultObservation).one()
    assert report.completed_games_proposed_create == 1
    assert report.completed_create_candidates_validated == 1
    assert report.unresolved_reviewed_duplicate_candidates == 0
    assert report.completed_observations_proposed == 1
    assert game.neutral_site is True
    assert game.venue_name == "History Field"
    assert observation.observed_at == game.game_date + timedelta(hours=6)
    assert db.query(GameProviderIdentity).filter(
        GameProviderIdentity.provider == "cfbd",
        GameProviderIdentity.game_id == game.id,
    ).count() == 1


def test_completed_only_quarantines_unknown_neutral_without_observation(db):
    report = NCAAFHistoricalResultsImportService(
        db,
        UnknownNeutralCFBDClient(),
    ).import_seasons([2025], dry_run=False, completed_only=True)

    assert report.quarantined_games == 1
    assert report.completed_games_proposed_create == 0
    assert report.completed_observations_proposed == 0
    assert db.query(Game).count() == 0
    assert db.query(GameProviderIdentity).count() == 0
    assert db.query(GameResultObservation).count() == 0