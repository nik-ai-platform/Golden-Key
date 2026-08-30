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

        for bookmaker in game_data.get(
            "bookmakers",
            []
        ):
            create_odds_snapshot(
                self.db,
                game.id,
                bookmaker
            )

        self.db.commit()

        self.monitor.log_import(
            "Imported odds",
            game_id=game.id,
            count=len(game_data.get("bookmakers", [])),
        )

    def _parse_game_time(
        self,
        commence_time: str
    ) -> datetime:
        return datetime.fromisoformat(
            commence_time.replace("Z", "+00:00")
        )

    def _extract_market_values(
        self,
        bookmaker: dict
    ) -> tuple[float | None, float | None, int | None, int | None, float | None]:
        spread_home = None
        spread_away = None
        moneyline_home = None
        moneyline_away = None
        total = None

        for market in bookmaker.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "h2h" and len(outcomes) >= 2:
                moneyline_home = outcomes[0].get("price")
                moneyline_away = outcomes[1].get("price")

            if key == "spreads" and outcomes:
                spread_home = outcomes[0].get("point")
                if len(outcomes) > 1:
                    spread_away = outcomes[1].get("point")

            if key == "totals" and outcomes:
                total = outcomes[0].get("point")

        return spread_home, spread_away, moneyline_home, moneyline_away, total
