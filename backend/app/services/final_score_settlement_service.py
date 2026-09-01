from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.game import Game
from app.services.result_settlement_service import ResultSettlementService
from app.services.sport_mapping_service import SportMappingService


logger = logging.getLogger(__name__)


@dataclass
class FinalScoreSyncSummary:
    sport: str
    fetched: int = 0
    matched: int = 0
    finalized: int = 0
    already_final: int = 0
    unmatched: int = 0
    skipped_not_final: int = 0
    settled: int = 0
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
            provider_game_id = row.get("id")
            provider_home = row.get("home_team")
            provider_away = row.get("away_team")
            provider_home_score = self._score_for_team(row, provider_home)
            provider_away_score = self._score_for_team(row, provider_away)
            local_context = {
                "id": None,
                "provider_game_id": None,
                "home_team": None,
                "away_team": None,
                "game_date": None,
            }
            try:
                if not self._is_completed(row):
                    summary.skipped_not_final += 1
                    continue

                if not provider_game_id:
                    summary.unmatched += 1
                    self._log_unmatched(internal_sport, row)
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
                    summary.unmatched += 1
                    self._log_unmatched(internal_sport, row)
                    continue

                summary.matched += 1
                local_context = {
                    "id": game.id,
                    "provider_game_id": game.provider_game_id,
                    "home_team": game.home_team.name,
                    "away_team": game.away_team.name,
                    "game_date": game.game_date,
                }
                parsed = self._extract_scores(row)
                if parsed is None:
                    raise ValueError("Completed provider event has invalid or missing scores")

                home_score, away_score = parsed
                winner_team_id = (
                    game.home_team_id
                    if home_score > away_score
                    else game.away_team_id
                    if away_score > home_score
                    else None
                )
                already_final = (
                    game.status == "final"
                    and game.home_score == home_score
                    and game.away_score == away_score
                    and game.winner_team_id == winner_team_id
                )

                game.home_score = home_score
                game.away_score = away_score
                game.winner_team_id = winner_team_id
                game.status = "final"
                if game.completed_at is None:
                    game.completed_at = datetime.now(UTC).replace(tzinfo=None)
                if already_final:
                    summary.already_final += 1
                else:
                    summary.finalized += 1
                db.commit()

                settlement = self.settlement_service.settle_game(
                    db=db,
                    game_id=game.id,
                )
                if settlement["settled"]:
                    summary.settled += 1
            except Exception as exc:
                db.rollback()
                summary.errors += 1
                logger.exception(
                    (
                        "Final score reconciliation failed sport=%s "
                        "provider_event_id=%s provider_home_team=%s "
                        "provider_away_team=%s provider_completed=%s "
                        "provider_status=%s "
                        "provider_home_score=%s provider_away_score=%s "
                        "local_game_id=%s local_provider_event_id=%s "
                        "local_home_team=%s local_away_team=%s "
                        "local_game_date=%s exception_class=%s "
                        "exception_message=%s"
                    ),
                    internal_sport,
                    provider_game_id,
                    provider_home,
                    provider_away,
                    row.get("completed"),
                    row.get("status"),
                    provider_home_score,
                    provider_away_score,
                    local_context["id"],
                    local_context["provider_game_id"],
                    local_context["home_team"],
                    local_context["away_team"],
                    local_context["game_date"],
                    type(exc).__name__,
                    str(exc),
                )

        return summary

    @staticmethod
    def _is_completed(row: dict[str, Any]) -> bool:
        return row.get("completed") is True

    @classmethod
    def _score_for_team(cls, row: dict[str, Any], team: Any) -> Any:
        if team is None:
            return None
        for score in row.get("scores") or []:
            if score.get("name") == team:
                return score.get("score")
        return None

    @staticmethod
    def _log_unmatched(sport: str, row: dict[str, Any]) -> None:
        logger.warning(
            (
                "Provider final did not match local game sport=%s "
                "provider_event_id=%s home_team=%s away_team=%s "
                "commence_time=%s"
            ),
            sport,
            row.get("id"),
            row.get("home_team"),
            row.get("away_team"),
            row.get("commence_time"),
        )

    @staticmethod
    def _extract_scores(
        row: dict[str, Any],
    ) -> tuple[int, int] | None:
        home_team = row.get("home_team")
        away_team = row.get("away_team")
        scores = row.get("scores")
        if not home_team or not away_team or not scores:
            return None

        home_value = FinalScoreSettlementService._score_for_team(row, home_team)
        away_value = FinalScoreSettlementService._score_for_team(row, away_team)
        try:
            return int(home_value), int(away_value)
        except (TypeError, ValueError):
            return None