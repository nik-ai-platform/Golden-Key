from sqlalchemy.orm import Session

from app.models.odds import Odds
from app.repositories.odds_repository import SNAPSHOT_FIELDS, save_odds


class OddsImporter:

    VERSION = "ODDS-IMPORTER-1.0"

    def import_odds(
        self,
        db: Session,
        odds_data: list,
    ):

        imported = []

        for item in odds_data:

            odds = Odds(
                game_id=item["game_id"],
                sportsbook=item["sportsbook"],
                **{
                    name: item[name] if name in SNAPSHOT_FIELDS[:5] else item.get(name)
                    for name in SNAPSHOT_FIELDS
                },
            )

            imported.append(save_odds(db, odds))

        return imported