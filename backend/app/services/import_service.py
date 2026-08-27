from app.core.config import settings
from app.services.monitoring_service import MonitoringService


class ImportService:

    def __init__(
        self,
        importer_factory=None,
        monitor=None,
    ):
        if importer_factory is None:
            from app.workers.game_importer import GameOddsImporter

            importer_factory = lambda db: GameOddsImporter(db)

        self.importer_factory = importer_factory
        self.monitor = monitor or MonitoringService()


    def import_games(
        self,
        db,
        sport
    ):
        if settings.PERF_IMPORT_MOCK:
            self.monitor.log_import(
                "Import mocked for performance run",
                sport=sport,
            )
            return []

        importer = self.importer_factory(db)

        return importer.import_games(
            sport
        )


def import_sport_games(
    db,
    sport
):
    return ImportService().import_games(
        db,
        sport
    )
