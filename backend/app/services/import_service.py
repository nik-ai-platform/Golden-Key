from app.workers.game_importer import GameOddsImporter


def import_sport_games(
    db,
    sport
):

    importer = GameOddsImporter(db)

    return importer.import_games(
        sport
    )
