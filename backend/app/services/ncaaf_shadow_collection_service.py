from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, exists, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.game import Game
from app.models.game_result_observation import GameResultObservation
from app.models.ncaaf_power_market_shadow_record import NcaafPowerMarketShadowRecord
from app.models.ncaaf_power_market_shadow_result import NcaafPowerMarketShadowResult
from app.models.odds import Odds
from app.services.ncaaf_power_market_shadow_service import (
    CREATED,
    INSUFFICIENT_HISTORY,
    NO_PREGAME_MARKET,
    REUSED,
    SHADOW_SPEC_VERSION,
    UNKNOWN_NEUTRAL,
    authoritative_result_available_as_of,
    create_shadow_record_for_game,
    evaluate_shadow_record,
)
from app.services.ncaaf_power_rating_service import MODEL_VERSION


logger = logging.getLogger(__name__)

MISSED_PROSPECTIVE_WINDOW = "MISSED_PROSPECTIVE_WINDOW"
NOT_FINAL = "NOT_FINAL"
GENERATION_HORIZON = timedelta(hours=24)


@dataclass
class ShadowGenerationSummary:
    shadow_enabled: bool
    eligible_candidates: int = 0
    created: int = 0
    reused: int = 0
    insufficient_history: int = 0
    no_pregame_market: int = 0
    unknown_neutral: int = 0
    missed_prospective_window: int = 0
    errors: int = 0


@dataclass
class ShadowSettlementSummary:
    shadow_enabled: bool
    eligible_existing_records: int = 0
    evaluated: int = 0
    reused: int = 0
    not_final: int = 0
    errors: int = 0


def shadow_collection_enabled() -> bool:
    return bool(settings.NCAAF_SHADOW_COLLECTION_ENABLED)


def collect_ncaaf_shadow_evidence(
    *,
    generated_at: datetime | None = None,
    session_factory=SessionLocal,
) -> ShadowGenerationSummary:
    summary = ShadowGenerationSummary(shadow_enabled=shadow_collection_enabled())
    if not summary.shadow_enabled:
        _log_generation(summary)
        return summary
    generated_at = _as_utc(generated_at or datetime.now(UTC))
    db = None
    try:
        _require_supported_spec()
        db = session_factory()
        candidates = _generation_candidate_ids(db, generated_at)
        summary.eligible_candidates = len(candidates)
        for game_id in candidates:
            try:
                with db.begin_nested():
                    if authoritative_result_available_as_of(db, game_id, generated_at):
                        summary.missed_prospective_window += 1
                        continue
                    outcome = create_shadow_record_for_game(
                        db,
                        game_id,
                        generated_at=generated_at,
                    )
                    if outcome.state == CREATED:
                        summary.created += 1
                    elif outcome.state == REUSED:
                        summary.reused += 1
                    elif outcome.state == INSUFFICIENT_HISTORY:
                        summary.insufficient_history += 1
                    elif outcome.state == NO_PREGAME_MARKET:
                        summary.no_pregame_market += 1
                    elif outcome.state == UNKNOWN_NEUTRAL:
                        summary.unknown_neutral += 1
            except Exception:
                summary.errors += 1
                logger.exception(
                    "NCAAF shadow generation candidate failed game_id=%s",
                    game_id,
                )
        db.commit()
    except Exception:
        if db is not None:
            db.rollback()
        summary.errors += 1
        logger.exception("NCAAF shadow generation failed")
    finally:
        if db is not None:
            db.close()
    _log_generation(summary)
    return summary


def settle_ncaaf_shadow_evidence(
    *,
    settled_at: datetime | None = None,
    session_factory=SessionLocal,
) -> ShadowSettlementSummary:
    summary = ShadowSettlementSummary(shadow_enabled=shadow_collection_enabled())
    if not summary.shadow_enabled:
        _log_settlement(summary)
        return summary
    settled_at = _as_utc(settled_at or datetime.now(UTC))
    db = None
    try:
        _require_supported_spec()
        db = session_factory()
        record_ids = _settlement_candidate_ids(db, settled_at)
        summary.eligible_existing_records = len(record_ids)
        for record_id in record_ids:
            try:
                with db.begin_nested():
                    outcome = evaluate_shadow_record(db, record_id, settled_at=settled_at)
                    if outcome.state == CREATED:
                        summary.evaluated += 1
                    elif outcome.state == REUSED:
                        summary.reused += 1
                    else:
                        summary.not_final += 1
            except Exception:
                summary.errors += 1
                logger.exception(
                    "NCAAF shadow settlement candidate failed shadow_record_id=%s",
                    record_id,
                )
        db.commit()
    except Exception:
        if db is not None:
            db.rollback()
        summary.errors += 1
        logger.exception("NCAAF shadow settlement failed")
    finally:
        if db is not None:
            db.close()
    _log_settlement(summary)
    return summary


def _generation_candidate_ids(db: Session, generated_at: datetime) -> list[int]:
    cutoff = generated_at.replace(tzinfo=None)
    horizon_start = (generated_at - GENERATION_HORIZON).replace(tzinfo=None)
    existing = exists().where(
        and_(
            NcaafPowerMarketShadowRecord.game_id == Game.id,
            NcaafPowerMarketShadowRecord.power_model_version == MODEL_VERSION,
            NcaafPowerMarketShadowRecord.shadow_spec_version == SHADOW_SPEC_VERSION,
        )
    )
    pregame_market = exists().where(
        and_(
            Odds.game_id == Game.id,
            Odds.created_at < Game.game_date,
            Odds.spread_home.is_not(None),
        )
    )
    return [
        game_id
        for (game_id,) in (
            db.query(Game.id)
            .filter(
                Game.sport == "NCAAF",
                Game.game_date > horizon_start,
                Game.game_date <= cutoff,
                pregame_market,
                ~existing,
            )
            .order_by(Game.game_date, Game.id)
            .all()
        )
    ]


def _settlement_candidate_ids(db: Session, settled_at: datetime) -> list[int]:
    cutoff = settled_at.replace(tzinfo=None)
    authoritative_observation = exists().where(
        and_(
            GameResultObservation.game_id == Game.id,
            GameResultObservation.status == "final",
            GameResultObservation.observed_at <= cutoff,
        )
    )
    return [
        record_id
        for (record_id,) in (
            db.query(NcaafPowerMarketShadowRecord.id)
            .join(Game, Game.id == NcaafPowerMarketShadowRecord.game_id)
            .outerjoin(
                NcaafPowerMarketShadowResult,
                NcaafPowerMarketShadowResult.shadow_record_id
                == NcaafPowerMarketShadowRecord.id,
            )
            .filter(
                NcaafPowerMarketShadowRecord.power_model_version == MODEL_VERSION,
                NcaafPowerMarketShadowRecord.shadow_spec_version == SHADOW_SPEC_VERSION,
                NcaafPowerMarketShadowResult.id.is_(None),
                Game.home_score.is_not(None),
                Game.away_score.is_not(None),
                or_(
                    and_(Game.completed_at.is_not(None), Game.completed_at <= cutoff),
                    authoritative_observation,
                ),
            )
            .order_by(NcaafPowerMarketShadowRecord.id)
            .all()
        )
    ]


def _require_supported_spec() -> None:
    if settings.NCAAF_SHADOW_SPEC_VERSION != SHADOW_SPEC_VERSION:
        raise RuntimeError(
            "Configured NCAAF shadow spec does not match deployed service: "
            f"{settings.NCAAF_SHADOW_SPEC_VERSION} != {SHADOW_SPEC_VERSION}"
        )


def _log_generation(summary: ShadowGenerationSummary) -> None:
    logger.info("NCAAF shadow generation summary %s", asdict(summary))


def _log_settlement(summary: ShadowSettlementSummary) -> None:
    logger.info("NCAAF shadow settlement summary %s", asdict(summary))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)