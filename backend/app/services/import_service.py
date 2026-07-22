class ImportService:

    def __init__(self):
        pass


    def import_games(
        self,
        db,
        sport
    ):

        from app.workers.game_importer import GameOddsImporter

        importer = GameOddsImporter(
            db
        )

        return importer.import_games(
            sport
        )


def import_sport_games(
    db,
    sport
):

    importer = GameOddsImporter(db)

    return importer.import_games(
        sport
    )
