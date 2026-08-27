from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.team import Team


class GameImporter:

    VERSION = "GAME-IMPORTER-1.0"

    def import_game(
        self,
        db: Session,
        data: dict,
    ) -> Game:
        sport = data["sport"].upper()
        home_team = self._get_or_create_team(
            db=db,
            name=data["home_team"],
            sport=sport,
        )
        away_team = self._get_or_create_team(
            db=db,
            name=data["away_team"],
            sport=sport,
        )
        imported = self.import_games(
            db=db,
            games_data=[
                {
                    "id": data["external_id"],
                    "home_team_id": home_team.id,
                    "away_team_id": away_team.id,
                    "start_time": data["commence_time"],
                    "sport": sport,
                    "league": sport,
                    "season": datetime.utcnow().year,
                }
            ],
        )
        return imported[0]

    def _get_or_create_team(
        self,
        db: Session,
        name: str,
        sport: str,
    ) -> Team:
        team = (
            db.query(Team)
            .filter(
                Team.name == name,
                Team.sport == sport,
            )
            .first()
        )
        if team:
            return team

        team = Team(
            name=name,
            sport=sport,
            league=sport,
        )
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    def import_games(
        self,
        db: Session,
        games_data: list,
    ):

        imported = []

        for item in games_data:

            game_identifier = item["id"]
            id_field = "external_id" if hasattr(Game, "external_id") else "provider_game_id"

            existing = (
                db.query(Game)
                .filter(getattr(Game, id_field) == game_identifier)
                .first()
            )

            if existing:

                imported.append(existing)

                continue

            raw_start_time = item.get("start_time") or item.get("game_date") or datetime.utcnow()
            start_time = raw_start_time

            if isinstance(raw_start_time, str):
                normalized = raw_start_time.replace("Z", "+00:00")
                try:
                    start_time = datetime.fromisoformat(normalized)
                    if start_time.tzinfo is not None:
                        start_time = (
                            start_time.astimezone(timezone.utc)
                            .replace(tzinfo=None)
                        )
                except ValueError:
                    start_time = datetime.utcnow()

            game = Game(
                provider_game_id=item["id"],
                home_team_id=item["home_team_id"],
                away_team_id=item["away_team_id"],
                game_date=start_time,
                sport=item.get("sport", "UNKNOWN"),
                league=item.get("league", item.get("sport", "UNKNOWN")),
                season=item.get("season"),
            )

            if hasattr(Game, "status"):
                game.status = "scheduled"

            db.add(game)

            db.commit()

            db.refresh(game)

            imported.append(game)

        return imported