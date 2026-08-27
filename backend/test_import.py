from app.database.session import SessionLocal

from app.workers.game_importer import GameOddsImporter


def main():

    db = SessionLocal()

    try:

        importer = GameOddsImporter(
            db
        )

        games = importer.import_games(
            "americanfootball_nfl"
        )

        print(
            f"Imported games: {len(games)}"
        )

        for game in games:

            print(
                game.id,
                game.home_team_id,
                game.away_team_id,
                game.game_date
            )

    finally:

        db.close()


if __name__ == "__main__":
    main()
