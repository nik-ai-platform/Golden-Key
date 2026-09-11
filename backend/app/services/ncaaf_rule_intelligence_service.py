from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.ncaaf_rule_registry import match_ncaaf_ats_rule
from app.models.game import Game
from app.models.ncaaf_rule_intelligence import NcaafRuleIntelligence
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult


def record_rule_intelligence_for_prediction(
    db: Session,
    prediction: Prediction,
    odds_snapshot: Odds | None,
) -> NcaafRuleIntelligence | None:
    if (prediction.market or "").lower() != "spread":
        return None
    if prediction.model_version != "NPI-4.0":
        return None
    if odds_snapshot is None:
        return None
    if prediction.odds_snapshot_id != odds_snapshot.id:
        raise ValueError("Prediction odds snapshot does not match tracker snapshot")

    game = db.get(Game, prediction.game_id)
    if game is None:
        raise ValueError(f"Game {prediction.game_id} not found")
    if (game.sport or "").upper() != "NCAAF":
        return None

    existing = (
        db.query(NcaafRuleIntelligence)
        .filter(NcaafRuleIntelligence.prediction_id == prediction.id)
        .one_or_none()
    )
    if existing is not None:
        return existing

    rule = match_ncaaf_ats_rule(
        spread_home=odds_snapshot.spread_home,
        spread_away=odds_snapshot.spread_away,
    )
    if rule is None:
        return None

    npi_selection = (prediction.selection or "").upper()
    if npi_selection not in {"HOME", "AWAY", "PASS"}:
        raise ValueError(f"Unsupported NPI selection: {prediction.selection}")
    comparison = (
        "NPI_PASS"
        if npi_selection == "PASS"
        else "AGREE"
        if npi_selection == rule.pick_side
        else "DISAGREE"
    )
    rule_pick_line = (
        odds_snapshot.spread_home
        if rule.pick_side == "HOME"
        else odds_snapshot.spread_away
    )
    if rule_pick_line is None:
        raise ValueError("Matched rule pick side has no spread")

    record = NcaafRuleIntelligence(
        prediction_id=prediction.id,
        game_id=prediction.game_id,
        odds_snapshot_id=odds_snapshot.id,
        model_version=prediction.model_version,
        rule_code=rule.code,
        rule_team_location=rule.team_location,
        rule_spread=rule.spread,
        rule_semantics=rule.semantics,
        rule_pick_side=rule.pick_side,
        rule_pick_line=rule_pick_line,
        npi_selection=npi_selection,
        comparison=comparison,
    )
    db.add(record)
    db.flush()
    return record


def settle_rule_intelligence_for_prediction(
    db: Session,
    prediction_result: PredictionResult,
    game: Game,
) -> NcaafRuleIntelligence | None:
    record = (
        db.query(NcaafRuleIntelligence)
        .filter(
            NcaafRuleIntelligence.prediction_id
            == prediction_result.prediction_id
        )
        .one_or_none()
    )
    if record is None:
        return None
    if game.home_score is None or game.away_score is None:
        raise ValueError(f"Game {game.id} has no final score")

    selected_score = (
        float(game.home_score)
        if record.rule_pick_side == "HOME"
        else float(game.away_score)
    )
    opponent_score = (
        float(game.away_score)
        if record.rule_pick_side == "HOME"
        else float(game.home_score)
    )
    adjusted_score = selected_score + float(record.rule_pick_line)
    record.rule_result = (
        "WIN"
        if adjusted_score > opponent_score
        else "LOSS"
        if adjusted_score < opponent_score
        else "PUSH"
    )
    record.npi_result = (
        None
        if record.npi_selection == "PASS"
        else str(prediction_result.outcome).upper()
    )
    record.settled_at = prediction_result.created_at or datetime.now(UTC)
    db.flush()
    return record