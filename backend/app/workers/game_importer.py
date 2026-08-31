from datetime import datetime

from sqlalchemy.orm import Session

from app.services.live_data_service import LiveDataService
from app.services.monitoring_service import MonitoringService
from app.services.odds_service import create_odds_snapshot
from app.models.team import Team
from app.models.game import Game


class GameOddsImporter:

    def __init__(
        self,
        db: Session,
        live_data_service=None,
        monitor=None,
    ):
        self.db = db
        self.live_data = (
            live_data_service or LiveDataService()
        )
        self.monitor = monitor or MonitoringService()

    def import_games(
        self,
        sport: str
    ):

        sport = sport.strip().upper()

        games = self.live_data.fetch_games(
            sport
        )

        imported = []

        for game_data in games:

            provider_game_id = game_data.get("id")
            if not provider_game_id:
                raise ValueError("Provider game is missing an id")

            home_team = self.get_or_create_team(
                game_data["home_team"],
                sport
            )

            away_team = self.get_or_create_team(
                game_data["away_team"],
                sport
            )

            game = (
                self.db.query(Game)
                .filter(Game.provider_game_id == provider_game_id)
                .first()
            )
            game_date = self._parse_game_time(
                game_data["commence_time"]
            )

            if game:
                game.sport = sport
                game.league = sport
                game.game_date = game_date
                game.home_team_id = home_team.id
                game.away_team_id = away_team.id
            else:
                game = Game(
                    provider_game_id=provider_game_id,
                    sport=sport,
                    league=sport,
                    season=game_date.year,
                    game_date=game_date,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                )
                self.db.add(game)

            self.db.commit()
            self.db.refresh(game)

            self.import_odds(
                game,
                game_data
            )

            imported.append(game)

        self.monitor.log_import(
            "Imported games",
            count=len(imported),
            sport=sport
        )

        return imported

    def get_or_create_team(
        self,
        name,
        sport
    ):

        team = (
            self.db.query(Team)
            .filter(
                Team.name == name
            )
            .first()
        )

        if team:
            return team

        team = Team(
            name=name,
            sport=sport,
            league=sport
        )

        self.db.add(team)
        self.db.commit()
        self.db.refresh(team)

        return team

    def import_odds(
        self,
        game,
        game_data
    ):

        imported_count = 0
        for bookmaker in game_data.get(
            "bookmakers",
            []
        ):
            odds = create_odds_snapshot(
                self.db,
                game.id,
                bookmaker
            )
            if odds is not None:
                imported_count += 1

        self.db.commit()

        self.monitor.log_import(
            "Imported odds",
            game_id=game.id,
            count=imported_count,
        )

    def _parse_game_time(
        self,
        commence_time: str
    ) -> datetime:
        return datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        )
