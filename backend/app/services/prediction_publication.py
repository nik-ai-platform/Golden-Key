"""One semantic supersession policy for customer publication; no row mutation."""

from collections.abc import Iterable

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.prediction_record import Prediction
from app.services.prediction_metric_contract import (
    metric_version, parse_market, supported_metadata, sql_market, sql_supported_metadata,
)


def canonical_predictions(predictions: Iterable[Prediction]) -> list[Prediction]:
    latest: dict[tuple[int, str], Prediction] = {}
    for prediction in predictions:
        market = parse_market(prediction.market)
        if market is None:
            continue
        key = (prediction.game_id, market)
        previous = latest.get(key)
        if previous is None or publication_order(prediction) > publication_order(previous):
            latest[key] = prediction
    return list(latest.values())


def publication_order(prediction: Prediction) -> tuple[int, int, int, int, int]:
    # Malformed metadata cannot replace a supported semantic prediction.
    major, minor = metric_version(prediction.model_version) or (0, 0)
    return (
        int((major, minor) != (0, 0)),
        int(supported_metadata(prediction.market, prediction.selection)),
        major, minor, prediction.id or 0,
    )


def canonical_prediction_id_query(
    game_ids: Iterable[int] | None = None, *, per_model_version: bool = False,
):
    """Rank before availability filters; materialize only winners, never history."""
    precedence = case(
        (Prediction.model_version == "NPI-5.0", 3),
        (Prediction.model_version == "NPI-4.1", 2),
        (Prediction.model_version == "NPI-4.0", 1),
        else_=0,
    )
    partition = (Prediction.game_id, sql_market(Prediction.market))
    if per_model_version:
        partition += (Prediction.model_version,)
    query = select(
        Prediction.id.label("prediction_id"),
        func.row_number().over(
            partition_by=partition,
            order_by=(
                case((precedence > 0, 1), else_=0).desc(),
                case((sql_supported_metadata(Prediction.market, Prediction.selection), 1), else_=0).desc(),
                precedence.desc(), Prediction.id.desc(),
            ),
        ).label("publication_rank"),
    ).where(sql_market(Prediction.market).is_not(None))
    if game_ids is not None:
        query = query.where(Prediction.game_id.in_(set(game_ids)))
    ranked = query.subquery()
    return select(ranked.c.prediction_id).where(ranked.c.publication_rank == 1)


def canonical_prediction_ids(db: Session, game_ids: Iterable[int]) -> set[int]:
    return set(db.scalars(canonical_prediction_id_query(game_ids)))
