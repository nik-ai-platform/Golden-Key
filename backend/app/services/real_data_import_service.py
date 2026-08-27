from sqlalchemy.orm import Session

from app.services.game_importer import GameImporter
from app.services.odds_importer import OddsImporter
from app.services.odds_normalizer_service import OddsNormalizerService
from app.services.odds_provider_client import OddsProviderClient
from app.services.sport_mapping_service import SportMappingService


class RealDataImportService:

    def __init__(self) -> None:
        self.client = OddsProviderClient()
        self.sport_mapping = SportMappingService()
        self.normalizer = OddsNormalizerService()
        self.game_importer = GameImporter()
        self.odds_importer = OddsImporter()

    def import_sport(
        self,
        db: Session,
        sport: str,
    ) -> dict:
        sport = sport.upper()
        provider_key = self.sport_mapping.provider_key(sport)
        payload = self.client.get_odds(provider_key)

        games_processed = 0
        odds_processed = 0
        errors = []

        for raw_game in payload:
            try:
                normalized_game = self.normalizer.normalize_game(
                    raw_game,
                    sport,
                )
                game = self.game_importer.import_game(
                    db=db,
                    data=normalized_game,
                )
                games_processed += 1

                normalized_odds = []
                for bookmaker in raw_game.get("bookmakers", []):
                    odds = self.normalizer.normalize_bookmaker(
                        raw_game,
                        bookmaker,
                    )
                    normalized_odds.append(
                        {
                            **odds,
                            "game_id": game.id,
                        }
                    )

                if normalized_odds:
                    self.odds_importer.import_odds(
                        db=db,
                        odds_data=normalized_odds,
                    )
                    odds_processed += len(normalized_odds)

            except Exception as error:
                db.rollback()
                errors.append(
                    {
                        "external_id": raw_game.get("id"),
                        "error": str(error),
                    }
                )

        return {
            "sport": sport,
            "provider_games": len(payload),
            "games_processed": games_processed,
            "odds_processed": odds_processed,
            "errors": errors,
        }
