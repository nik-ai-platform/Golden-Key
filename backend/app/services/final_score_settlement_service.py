from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.game import Game
from app.services.result_settlement_service import ResultSettlementService
from app.services.sport_mapping_service import SportMappingService


@dataclass
class FinalScoreSyncSummary:
    sport: str
    fetched: int = 0
    matched: int = 0
    updated: int = 0
    settled: int = 0
    skipped: int = 0
    errors: int = 0


class FinalScoreSettlementService:
    def __init__(
        self,
        *,
        provider_client,
        settlement_service: ResultSettlementService | None = None,
        sport_mapping: SportMappingService | None = None,
    ) -> None:
        self.provider_client = provider_client
        self.settlement_service = settlement_service or ResultSettlementService()
        self.sport_mapping = sport_mapping or SportMappingService()

    def sync_sport(
        self,
        db: Session,
        sport: str,
        *,
        days_from: int = 3,
    ) -> FinalScoreSyncSummary:
        internal_sport = sport.upper()
        provider_sport = self.sport_mapping.provider_key(internal_sport)
        score_rows = self.provider_client.get_scores(
            provider_sport,
            days_from=days_from,
        )
        summary = FinalScoreSyncSummary(
            sport=internal_sport,
            fetched=len(score_rows),
        )

        for row in score_rows:
            try:
                if not self._is_completed(row):
                    summary.skipped += 1
                    continue

                provider_game_id = row.get("id")
                if not provider_game_id:
                    summary.skipped += 1
                    continue

                game = (
                    db.query(Game)
                    .filter(
                        Game.provider_game_id == provider_game_id,
                        Game.sport == internal_sport,
                    )
                    .one_or_none()
                )
                if game is None:
                    summary.skipped += 1
                    continue

                summary.matched += 1
                parsed = self._extract_scores(row)
                if parsed is None:
                    summary.skipped += 1
                    continue

                home_score, away_score = parsed
                winner_team_id = (
                    game.home_team_id
                    if home_score > away_score
                    else game.away_team_id
                    if away_score > home_score
                    else None
                )
                changed = (
                    game.home_score != home_score
                    or game.away_score != away_score
                    or game.winner_team_id != winner_team_id
                )

                game.home_score = home_score
                game.away_score = away_score
                game.winner_team_id = winner_team_id
                if changed:
                    summary.updated += 1
                db.commit()

                settlement = self.settlement_service.settle_game(
                    db=db,
                    game_id=game.id,
                )
                if settlement["settled"]:
                    summary.settled += 1
                else:
                    summary.skipped += 1
            except Exception:
                db.rollback()
                summary.errors += 1

        return summary

    @staticmethod
    def _is_completed(row: dict[str, Any]) -> bool:
        return row.get("completed") is True

    @staticmethod
    def _extract_scores(
        row: dict[str, Any],
    ) -> tuple[int, int] | None:
        home_team = row.get("home_team")
        away_team = row.get("away_team")
        scores = row.get("scores")
        if not home_team or not away_team or not scores:
            return None

        by_name: dict[str, int] = {}
        for score in scores:
            name = score.get("name")
            value = score.get("score")
            if name is None or value is None:
                continue
            try:
                by_name[name] = int(value)
            except (TypeError, ValueError):
                continue

        if home_team not in by_name or away_team not in by_name:
            return None

        return by_name[home_team], by_name[away_team]