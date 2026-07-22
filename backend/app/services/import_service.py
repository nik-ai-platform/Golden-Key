import logging

from app.workers.game_importer import GameOddsImporter


logger = logging.getLogger(__name__)


class ImportService:

    def __init__(self, db=None):
        self.db = db

    def run(self, sport: str | None = None):
        if self.db is None or sport is None:
            logger.info("ImportService.run skipped: missing db or sport.")
            return []

        importer = GameOddsImporter(self.db)
        return importer.import_games(sport)


def import_sport_games(
    db,
    sport
):

    importer = GameOddsImporter(db)

    return importer.import_games(
        sport
    )
