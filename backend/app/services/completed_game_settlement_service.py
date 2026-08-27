from sqlalchemy.orm import Session

from app.models.game import Game
from app.services.result_settlement_service import ResultSettlementService


class CompletedGameSettlementService:

    def __init__(self) -> None:
        self.settlement = ResultSettlementService()

    def settle_completed_games(
        self,
        db: Session,
        sport: str | None = None,
    ) -> dict:
        query = db.query(Game)
        if sport:
            query = query.filter(Game.sport == sport.upper())

        settled_games = []
        skipped_games = []
        failures = []
        for game in query.all():
            if game.home_score is None or game.away_score is None:
                skipped_games.append(game.id)
                continue
            try:
                settled_games.append(
                    self.settlement.settle_game(
                        db=db,
                        game_id=game.id,
                    )
                )
            except Exception as error:
                db.rollback()
                failures.append(
                    {
                        "game_id": game.id,
                        "error": str(error),
                    }
                )

        return {
            "sport": sport.upper() if sport else "ALL",
            "settled_games": len(settled_games),
            "skipped_games": len(skipped_games),
            "failures": failures,
            "results": settled_games,
        }
