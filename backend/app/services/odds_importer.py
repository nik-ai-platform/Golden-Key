from sqlalchemy.orm import Session

from app.models.odds import Odds


class OddsImporter:

    VERSION = "ODDS-IMPORTER-1.0"

    def import_odds(
        self,
        db: Session,
        odds_data: list,
    ):

        imported = []

        for item in odds_data:

            existing = (
                db.query(Odds)
                .filter(
                    Odds.game_id == item["game_id"],
                    Odds.sportsbook == item["sportsbook"],
                )
                .first()
            )

            if existing:
                existing.spread_home = item["spread_home"]
                existing.spread_away = item["spread_away"]
                existing.moneyline_home = item["moneyline_home"]
                existing.moneyline_away = item["moneyline_away"]
                existing.total = item["total"]

                db.commit()
                db.refresh(existing)
                imported.append(existing)
                continue

            odds = Odds(
                game_id=item["game_id"],
                sportsbook=item["sportsbook"],
                spread_home=item["spread_home"],
                spread_away=item["spread_away"],
                moneyline_home=item["moneyline_home"],
                moneyline_away=item["moneyline_away"],
                total=item["total"],
            )

            db.add(odds)

            db.commit()

            db.refresh(odds)

            imported.append(odds)

        return imported