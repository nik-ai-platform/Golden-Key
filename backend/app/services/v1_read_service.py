from datetime import UTC, date, datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy.orm import Session, aliased

from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.services.performance_scope import regular_season_games
from app.models.team import Team
from app.models.user_prediction import UserPrediction
from app.services.prediction_metric_contract import (
    actionable_prediction, describe_edge, edge_ranking_strength, finite_metric,
    historical_price, historical_text, metric_reasoning, normalized_text,
    parse_market, parse_selection, selected_side_probability, sql_selection, sql_supported_metadata,
    supported_metadata,
)
from app.services.prediction_publication import canonical_prediction_id_query
from app.services.recommendation_eligibility import (
    is_recommendation_eligible,
    moneyline_price_tier,
    recommendation_designation,
)


def _utc_iso(value: datetime | None) -> str | None:
    """
    Serialize game timestamps as explicit UTC.

    Golden Key stores game_date as naive UTC in Postgres.
    Adding the UTC timezone before serialization prevents browsers
    from interpreting the stored UTC clock time as local time.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)

    return value.isoformat().replace("+00:00", "Z")


@dataclass
class _OutcomeCounts:
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    units: float = 0.0

    def add(self, result: PredictionResult) -> None:
        outcome = normalized_text(result.outcome, upper=True)
        self.wins += outcome == "WIN"
        self.losses += outcome == "LOSS"
        self.pushes += outcome == "PUSH"
        self.units += float(result.profit_loss or 0.0) / 100.0

    def summary(self) -> dict:
        graded = self.wins + self.losses
        total = graded + self.pushes
        return {
            "total_bets": total, "wins": self.wins, "losses": self.losses,
            "pushes": self.pushes,
            "win_rate": round(self.wins / graded * 100, 2) if graded else 0.0,
            "units_won": round(self.units, 2),
            "roi": round(self.units / total * 100, 2) if total else 0.0,
        }

    def spread_summary(self) -> dict:
        summary = self.summary()
        return {
            "sample_size": summary["total_bets"], "wins": self.wins,
            "losses": self.losses, "pushes": self.pushes,
            "win_rate": summary["win_rate"], "units": summary["units_won"],
            "roi": summary["roi"],
        }


class _HistoricalSpreadReport:
    PROBABILITY_BANDS = (
        (55, "50-54.9"), (60, "55-59.9"), (65, "60-64.9"),
        (70, "65-69.9"), (101, "70+"),
    )

    def __init__(self):
        self.summary = _OutcomeCounts()
        self.bands = {
            name: {key: _OutcomeCounts() for key in keys}
            for name, keys in (
                ("npi_bands", ("0-99", "100-124", "125-149", "150-174", "175-200")),
                ("confidence_bands", ("<60", "60-69", "70-79", "80-89", "90-100")),
                ("projected_edge_bands", ("5-9.9", "10-14.9", "15-19.9", "20+")),
            )
        }
        self.calibration = {key: _OutcomeCounts() for _, key in self.PROBABILITY_BANDS}
        self.probability_sums = {key: 0.0 for key in self.calibration}
        self.brier_sum = 0.0
        self.brier_count = 0

    @classmethod
    def probability_key(cls, probability: float) -> str | None:
        return next(
            (label for ceiling, label in cls.PROBABILITY_BANDS if 50 <= probability < ceiling),
            None,
        )

    def add(self, prediction, result, band_keys) -> None:
        self.summary.add(result)
        for name, key in zip(self.bands, band_keys):
            if key in self.bands[name]:
                self.bands[name][key].add(result)
        probability = selected_side_probability(
            prediction.simulation_probability, market=prediction.market,
            selection=prediction.selection, model_version=prediction.model_version,
        )
        if probability is None:
            return
        key = self.probability_key(probability)
        if key is not None:
            self.calibration[key].add(result)
            self.probability_sums[key] += probability
        outcome = normalized_text(result.outcome, upper=True)
        if outcome in {"WIN", "LOSS"}:
            self.brier_sum += (probability / 100 - float(outcome == "WIN")) ** 2
            self.brier_count += 1

    def report(self) -> dict:
        calibration = []
        for key, counts in self.calibration.items():
            summary = counts.spread_summary()
            total = summary["sample_size"]
            calibration.append({
                "key": key, "sample_size": total, "wins": counts.wins,
                "losses": counts.losses, "pushes": counts.pushes,
                "predicted_probability_average": round(self.probability_sums[key] / total, 2) if total else 0.0,
                "actual_win_rate": summary["win_rate"],
            })
        return {
            "summary": self.summary.spread_summary(),
            **{
                name: [{"key": key, **counts.spread_summary()} for key, counts in buckets.items()]
                for name, buckets in self.bands.items()
            },
            "probability_calibration": calibration,
            "brier_score": round(self.brier_sum / self.brier_count, 4) if self.brier_count else None,
            "brier_sample_size": self.brier_count,
        }


class V1ReadService:

    LONG_MONEYLINE_ODDS = 500
    UPCOMING_HORIZON_DAYS = 14
    DAILY_CARD_MARKETS = (
        ("spread", "TOP_SPREAD", "Top Spread"),
        ("moneyline", "TOP_MONEYLINE", "Moneyline Value"),
        ("total", "TOP_TOTAL", "Top Total"),
    )

    def get_daily_card(
        self,
        db: Session,
        sport: str | None = None,
    ) -> dict:
        feed = self.get_today_predictions(
            db=db,
            sport=sport,
            include_passes=False,
        )
        card = self._build_daily_card(feed["predictions"])
        return {
            "sport": sport.upper() if sport else None,
            "generated_at": _utc_iso(datetime.now(UTC)),
            "slate_date": feed["slate_date"],
            **card,
        }

    def resolve_slate_date(
        self,
        db: Session,
        *,
        sport: str | None = None,
        include_passes: bool = False,
    ) -> date:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today = now.date()
        window_end = now + timedelta(days=14)
        items = self._prediction_items_for_window(
            db=db, start_at=now, end_at=window_end, sport=sport,
            include_passes=include_passes, scheduled_only=False,
        )
        dates = [
            date.fromisoformat(item["game_date"][:10])
            for item in items
            if include_passes or item["recommendation_eligible"]
        ]
        return min(dates) if dates else today

    def _build_daily_card(self, predictions: list[dict]) -> dict:
        ranked = sorted(
            [
                prediction for prediction in predictions
                if actionable_prediction(prediction)
                and prediction.get("recommendation_eligible") is not False
                and is_recommendation_eligible(prediction.get("market"), prediction.get("american_odds"))
            ],
            key=lambda prediction: (
                -self._daily_card_score(prediction),
                -float(prediction.get("confidence_score") or 0),
                -(edge_ranking_strength(describe_edge(
                    prediction.get("projected_edge"), market=prediction["market"],
                    selection=prediction["selection"], model_version=prediction["model_version"],
                ).selected_side_value, prediction["market"]) or 0),
                prediction["prediction_id"],
            ),
        )
        recommendation_ranked = [
            prediction
            for prediction in ranked
            if is_recommendation_eligible(
                prediction.get("market"),
                prediction.get("american_odds"),
            )
            and parse_selection(prediction.get("selection")) != "PASS"
            and prediction.get("recommendation_eligible") is not False
        ]
        used_ids = set()
        primary_candidates = [
            prediction
            for prediction in recommendation_ranked
            if not self._is_long_moneyline(prediction)
        ]
        best_prediction = primary_candidates[0] if primary_candidates else None
        best_bet = None
        if best_prediction:
            best_bet = self._daily_card_pick(
                best_prediction,
                role="BEST_BET",
                label="Best Bet",
            )
            used_ids.add(best_prediction["prediction_id"])

        featured_picks = []
        for market, role, label in self.DAILY_CARD_MARKETS:
            prediction = next(
                (
                    item
                    for item in recommendation_ranked
                    if parse_market(item["market"]) == market
                    and item["prediction_id"] not in used_ids
                ),
                None,
            )
            if prediction:
                featured_picks.append(
                    self._daily_card_pick(prediction, role=role, label=label)
                )
                used_ids.add(prediction["prediction_id"])

        value_prediction = next(
            (
                prediction
                for prediction in recommendation_ranked
                if prediction["prediction_id"] not in used_ids
                and parse_market(prediction["market"]) == "spread"
                and float(prediction.get("line_value") or 0) > 0
            ),
            None,
        )
        if value_prediction:
            featured_picks.append(
                self._daily_card_pick(
                    value_prediction,
                    role="VALUE_PLAY",
                    label="Value Play",
                )
            )
            used_ids.add(value_prediction["prediction_id"])

        next_best = [
            self._daily_card_pick(
                prediction,
                role="NEXT_BEST",
                label="Next Best Pick",
            )
            for prediction in recommendation_ranked
            if prediction["prediction_id"] not in used_ids
        ][:3]
        return {
            "count": len(predictions),
            "best_bet": best_bet,
            "featured_picks": featured_picks,
            "next_best": next_best,
        }

    def _daily_card_pick(self, prediction: dict, *, role: str, label: str) -> dict:
        reasons = [f"NPI {float(prediction['npi_score']):.1f} / 200"]
        confidence = prediction.get("confidence_score")
        edge = prediction.get("projected_edge")
        descriptor = describe_edge(
            edge, market=prediction["market"], selection=prediction["selection"],
            model_version=prediction["model_version"],
        )
        if confidence is not None:
            reasons.append(f"{float(confidence):.1f}% Confidence Rating")
        if descriptor.selected_side_value is not None:
            unit = "points" if descriptor.unit == "scoring_points" else "pp"
            reasons.append(f"{descriptor.selected_side_value:.1f} {unit} projected edge")
        return {
            "role": role,
            "label": label,
            "ranking_reasons": reasons,
            "prediction": prediction,
        }

    @staticmethod
    def _bounded(value, lower=0.0, upper=100.0) -> float:
        return max(lower, min(float(value or 0), upper))

    def _daily_card_score(self, prediction: dict) -> float:
        npi = self._bounded(float(prediction.get("npi_score") or 0) / 2)
        confidence = self._bounded(prediction.get("confidence_score"))
        simulation = self._bounded(prediction.get("simulation_probability"))
        edge = self._bounded(
            (edge_ranking_strength(describe_edge(
                    prediction.get("projected_edge"),
                    market=prediction["market"], selection=prediction["selection"],
                    model_version=prediction["model_version"],
                ).selected_side_value, prediction["market"]) or 0) * 50
        )
        return round(
            npi * 0.35
            + confidence * 0.30
            + simulation * 0.20
            + edge * 0.15,
            2,
        )

    def _is_long_moneyline(self, prediction: dict) -> bool:
        return (
            parse_market(prediction["market"]) == "moneyline"
            and float(prediction.get("american_odds") or 0)
            >= self.LONG_MONEYLINE_ODDS
        )

    def get_today_predictions(
        self,
        db: Session,
        sport: str | None = None,
        include_passes: bool = False,
    ) -> dict:
        slate_date = self.resolve_slate_date(
            db,
            sport=sport,
            include_passes=include_passes,
        )
        day_start = datetime.combine(slate_date, datetime.min.time())
        day_end = day_start.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        items = self._prediction_items_for_window(
            db=db,
            start_at=max(
                day_start,
                now if day_start == today_start else day_start,
            ),
            end_at=day_end,
            sport=sport,
            include_passes=include_passes,
            scheduled_only=False,
        )
        return {
            "sport": sport.upper() if sport else None,
            "slate_date": slate_date.isoformat(),
            "count": len(items),
            "predictions": items,
        }

    def get_upcoming_predictions(
        self,
        db: Session,
        sport: str | None = None,
        include_passes: bool = False,
    ) -> dict:
        start_at = datetime.now(timezone.utc).replace(tzinfo=None)
        end_at = start_at + timedelta(days=self.UPCOMING_HORIZON_DAYS)
        items = self._prediction_items_for_window(
            db=db,
            start_at=start_at,
            end_at=end_at,
            sport=sport,
            include_passes=include_passes,
            scheduled_only=True,
        )
        return {
            "sport": sport.upper() if sport else None,
            "start_date": _utc_iso(start_at),
            "end_date": _utc_iso(end_at),
            "count": len(items),
            "predictions": items,
        }

    def _prediction_items_for_window(
        self,
        *,
        db: Session,
        start_at: datetime,
        end_at: datetime,
        sport: str | None,
        include_passes: bool,
        scheduled_only: bool,
    ) -> list[dict]:
        home_team = aliased(Team)
        away_team = aliased(Team)
        query = (
            db.query(Prediction, Game, home_team, away_team)
            .join(Game, Game.id == Prediction.game_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .filter(Prediction.id.in_(canonical_prediction_id_query()))
        )
        if sport:
            query = query.filter(Game.sport == sport.upper())
        query = query.filter(
            Game.status == "scheduled" if scheduled_only else Game.status != "final"
        )

        rows = query.filter(
            Game.game_date >= start_at,
            Game.game_date <= end_at,
        ).order_by(
            Prediction.id.desc(),
            Prediction.confidence_score.desc(),
            Prediction.npi_score.desc(),
        ).all()
        items = [
            self._prediction_item(prediction, game, home, away)
            for prediction, game, home, away in rows
            if include_passes or actionable_prediction(prediction)
        ]
        return items

    def get_game_detail(
        self,
        db: Session,
        game_id: int,
    ) -> dict:
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise ValueError(f"Game {game_id} not found")

        home_team = (
            db.query(Team)
            .filter(Team.id == game.home_team_id)
            .first()
        )
        away_team = (
            db.query(Team)
            .filter(Team.id == game.away_team_id)
            .first()
        )
        prediction_rows = (
            db.query(Prediction)
            .filter(Prediction.game_id == game_id)
            .filter(Prediction.id.in_(canonical_prediction_id_query([game_id])))
            .order_by(Prediction.id.desc())
            .all()
        )
        latest_by_market = {
            parse_market(prediction.market): prediction
            for prediction in prediction_rows
        }
        selected_predictions = [
            latest_by_market[market]
            for market in ("spread", "moneyline", "total")
            if market in latest_by_market
        ]
        outcomes = {
            result.prediction_id: result.outcome
            for result in db.query(PredictionResult)
            .filter(
                PredictionResult.prediction_id.in_(
                    [prediction.id for prediction in selected_predictions]
                )
            )
            .all()
        } if selected_predictions else {}
        return {
            "game_id": game.id,
            "sport": game.sport,
            "home_team": (
                home_team.name if home_team else str(game.home_team_id)
            ),
            "away_team": (
                away_team.name if away_team else str(game.away_team_id)
            ),
            "game_date": _utc_iso(game.game_date),
            "home_score": game.home_score,
            "away_score": game.away_score,
            "predictions": [
                {
                    **self._prediction_item(
                        prediction,
                        game,
                        home_team,
                        away_team,
                    ),
                    "outcome": outcomes.get(prediction.id),
                }
                for prediction in selected_predictions
            ],
        }

    def get_saved_picks(
        self,
        db: Session,
        user_id: int,
    ) -> dict:
        home_team = aliased(Team)
        away_team = aliased(Team)
        rows = (
            db.query(
                UserPrediction,
                Prediction,
                Game,
                home_team,
                away_team,
            )
            .join(
                Prediction,
                Prediction.id == UserPrediction.prediction_id,
            )
            .join(Game, Game.id == Prediction.game_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .filter(UserPrediction.user_id == user_id)
            .all()
        )
        picks = []
        for saved, prediction, game, home, away in rows:
            result = (
                db.query(PredictionResult)
                .filter(PredictionResult.prediction_id == prediction.id)
                .first()
            )
            picks.append(
                {
                    "saved_pick_id": saved.id,
                    "prediction_id": prediction.id,
                    "game_id": prediction.game_id,
                    "sport": game.sport,
                    "game_date": _utc_iso(game.game_date),
                    "home_team": home.name,
                    "away_team": away.name,
                    "matchup": f"{away.name} @ {home.name}",
                    "market": parse_market(prediction.market) or "unavailable",
                    "selection": parse_selection(prediction.selection) if supported_metadata(
                        prediction.market, prediction.selection,
                    ) else "unavailable",
                    "display_selection": self._display_selection(
                        prediction,
                        home,
                        away,
                    ),
                    "line_value": finite_metric(prediction.line_value),
                    "american_odds": historical_price(prediction.american_odds),
                    "npi_score": finite_metric(prediction.npi_score),
                    "confidence_score": finite_metric(prediction.confidence_score),
                    "risk_level": historical_text(prediction.risk_level),
                    "outcome": result.outcome if result else None,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                }
            )
        return {
            "count": len(picks),
            "picks": picks,
        }

    def get_performance(self, db: Session) -> dict:
        home_team = aliased(Team)
        away_team = aliased(Team)
        rows = (
            db.query(
                PredictionResult,
                Prediction,
                Game,
                home_team,
                away_team,
            )
            .join(
                Prediction,
                Prediction.id == PredictionResult.prediction_id,
            )
            .join(Game, Game.id == Prediction.game_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .filter(PredictionResult.outcome.in_(("WIN", "LOSS", "PUSH")))
            .filter(regular_season_games())
            .filter(Prediction.id.in_(canonical_prediction_id_query()))
            .filter(sql_supported_metadata(Prediction.market, Prediction.selection))
            .filter(sql_selection(Prediction.selection).is_not(None), sql_selection(Prediction.selection) != "PASS")
            .order_by(Game.game_date.desc(), PredictionResult.id.desc())
            .all()
        )
        wins = sum(result.outcome == "WIN" for result, *_ in rows)
        losses = sum(result.outcome == "LOSS" for result, *_ in rows)
        pushes = sum(result.outcome == "PUSH" for result, *_ in rows)
        graded = wins + losses
        accuracy = wins / graded * 100 if graded else 0.0
        profit_loss = sum(float(result.profit_loss or 0) for result, *_ in rows)

        def breakdown(group_by_market: bool) -> list[dict]:
            grouped: dict[str, list[PredictionResult]] = {}
            for result, prediction, game, *_ in rows:
                name = (
                    parse_market(prediction.market) or "unavailable"
                    if group_by_market
                    else game.sport.upper()
                )
                grouped.setdefault(name, []).append(result)

            items = []
            for name, group in grouped.items():
                group_wins = sum(result.outcome == "WIN" for result in group)
                group_losses = sum(result.outcome == "LOSS" for result in group)
                group_pushes = sum(result.outcome == "PUSH" for result in group)
                decisions = group_wins + group_losses
                items.append(
                    {
                        "name": name,
                        "settled": len(group),
                        "wins": group_wins,
                        "losses": group_losses,
                        "pushes": group_pushes,
                        "win_rate": (
                            round(group_wins / decisions * 100, 2)
                            if decisions
                            else None
                        ),
                    }
                )
            return items

        return {
            "total_predictions": len(rows),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "accuracy": round(accuracy, 2),
            "profit_loss": round(profit_loss, 2),
            "market_performance": breakdown(True),
            "sport_performance": breakdown(False),
            "recent_results": [
                {
                    "prediction_id": prediction.id,
                    "game_id": game.id,
                    "sport": game.sport,
                    "game_date": _utc_iso(game.game_date),
                    "home_team": home.name,
                    "away_team": away.name,
                    "market": parse_market(prediction.market) or "unavailable",
                    "display_selection": self._display_selection(
                        prediction,
                        home,
                        away,
                    ),
                    "npi_score": finite_metric(prediction.npi_score),
                    "outcome": result.outcome,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                }
                for result, prediction, game, home, away in rows[:10]
            ],
        }

    def get_performance_intelligence(
        self,
        db,
        days: int = 30,
    ) -> dict:
        if days not in {7, 30, 90}:
            days = 30

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now - timedelta(days=days)

        history_query = (
            db.query(Prediction, PredictionResult, Game)
            .join(
                PredictionResult,
                PredictionResult.prediction_id == Prediction.id,
            )
            .join(
                Game,
                Game.id == Prediction.game_id,
            )
            .filter(PredictionResult.created_at >= cutoff)
            .filter(PredictionResult.outcome.in_(["WIN", "LOSS", "PUSH"]))
            .filter(regular_season_games())
        )
        customer_rows = history_query.filter(
            Prediction.id.in_(canonical_prediction_id_query()),
            sql_supported_metadata(Prediction.market, Prediction.selection),
            sql_selection(Prediction.selection).is_not(None), sql_selection(Prediction.selection) != "PASS",
        ).all()
        def summarize(items) -> dict:
            counts = _OutcomeCounts()
            for _, result, _ in items:
                counts.add(result)
            return counts.summary()

        def grouped(items, key_fn) -> list[dict]:
            buckets: dict[str, list] = {}

            for item in items:
                key = key_fn(*item)

                if key is None:
                    continue

                key = str(key)
                buckets.setdefault(key, []).append(item)

            return [
                {
                    "key": key,
                    **summarize(bucket),
                }
                for key, bucket in sorted(buckets.items())
            ]

        def npi_band(prediction, result, game):
            value = finite_metric(prediction.npi_score)

            if value is None:
                return "Unknown"
            if value < 100:
                return "0-99"
            if value < 125:
                return "100-124"
            if value < 150:
                return "125-149"
            if value < 175:
                return "150-174"
            return "175-200"

        def confidence_band(prediction, result, game):
            value = finite_metric(prediction.confidence_score)

            if value is None:
                return "Unknown"
            if value < 60:
                return "<60"
            if value < 70:
                return "60-69"
            if value < 80:
                return "70-79"
            if value < 90:
                return "80-89"
            return "90-100"

        def odds_band(prediction, result, game):
            odds = historical_price(prediction.american_odds)

            if odds is None:
                return "Unknown"

            odds = int(odds)

            if odds >= 500:
                return "+500 or longer"
            if odds >= 200:
                return "+200 to +499"
            if odds >= 100:
                return "+100 to +199"
            if odds <= -200:
                return "-200 or shorter"
            if odds <= -101:
                return "-101 to -199"

            return "Other"

        def side_type(prediction, result, game):
            market = parse_market(prediction.market)
            odds = historical_price(prediction.american_odds)

            if market not in {"spread", "moneyline"}:
                return "Other"

            if odds is not None:
                if odds > 0:
                    return "Underdog"
                if odds < 0:
                    return "Favorite"

            return "Unknown"

        def projected_edge_band(prediction, result, game):
            value = finite_metric(prediction.projected_edge)
            if value is None:
                return None
            value = abs(float(value))
            if value < 5:
                return None
            if value < 10:
                return "5-9.9"
            if value < 15:
                return "10-14.9"
            if value < 20:
                return "15-19.9"
            return "20+"

        versions: dict[str, _OutcomeCounts] = {}
        spreads = {version: _HistoricalSpreadReport() for version in ("NPI-4.0", "NPI-5.0")}
        # Audit reporting streams bounded batches; counters never retain ORM history.
        version_history = history_query.filter(
            Prediction.id.in_(canonical_prediction_id_query(per_model_version=True)),
        )
        for prediction, result, game in version_history.order_by(PredictionResult.id).yield_per(200):
            version = historical_text(prediction.model_version) or "Unknown"
            versions.setdefault(version, _OutcomeCounts()).add(result)
            if (
                version in spreads and parse_market(prediction.market) == "spread"
                and parse_selection(prediction.selection) != "PASS"
            ):
                spreads[version].add(prediction, result, (
                    npi_band(prediction, result, game),
                    confidence_band(prediction, result, game),
                    projected_edge_band(prediction, result, game),
                ))

        return {
            "period_days": days,
            "generated_at": now.isoformat() + "Z",
            "overall": summarize(customer_rows),
            "by_market": grouped(customer_rows, lambda p, r, g: (parse_market(p.market) or "Unknown").upper()),
            "by_sport": grouped(customer_rows, lambda p, r, g: (g.sport or "Unknown").upper()),
            "by_npi_band": grouped(customer_rows, npi_band),
            "by_confidence_band": grouped(customer_rows, confidence_band),
            "by_odds_band": grouped(customer_rows, odds_band),
            "by_side_type": grouped(customer_rows, side_type),
            "by_model_version": [
                {"key": key, **counts.summary()} for key, counts in sorted(versions.items())
            ],
            "npi_4_spread": spreads["NPI-4.0"].report(),
            "npi_5_spread": spreads["NPI-5.0"].report(),
        }

    @staticmethod
    def _spread_probability_calibration(items) -> tuple[list[dict], list[float]]:
        probability_keys = tuple(label for _, label in _HistoricalSpreadReport.PROBABILITY_BANDS)
        probability_buckets = {key: [] for key in probability_keys}
        brier_values = []
        for prediction, result, game in items:
            probability = selected_side_probability(
                prediction.simulation_probability, market=prediction.market,
                selection=prediction.selection, model_version=prediction.model_version,
            )
            if probability is None:
                continue
            key = _HistoricalSpreadReport.probability_key(probability)
            if key is not None:
                probability_buckets[key].append(
                    (prediction, result, game, probability)
                )
            outcome = (result.outcome or "").upper()
            if outcome in {"WIN", "LOSS"}:
                observed = 1.0 if outcome == "WIN" else 0.0
                brier_values.append((probability / 100.0 - observed) ** 2)

        probability_calibration = []
        for key in probability_keys:
            bucket = probability_buckets[key]
            wins = sum(
                1 for _, result, _, _ in bucket
                if (result.outcome or "").upper() == "WIN"
            )
            losses = sum(
                1 for _, result, _, _ in bucket
                if (result.outcome or "").upper() == "LOSS"
            )
            pushes = sum(
                1 for _, result, _, _ in bucket
                if (result.outcome or "").upper() == "PUSH"
            )
            graded = wins + losses
            probability_calibration.append(
                {
                    "key": key,
                    "sample_size": len(bucket),
                    "wins": wins,
                    "losses": losses,
                    "pushes": pushes,
                    "predicted_probability_average": (
                        round(
                            sum(item[3] for item in bucket) / len(bucket),
                            2,
                        )
                        if bucket
                        else 0.0
                    ),
                    "actual_win_rate": (
                        round((wins / graded) * 100.0, 2)
                        if graded
                        else 0.0
                    ),
                }
            )

        return probability_calibration, brier_values

    def _prediction_item(
        self,
        prediction: Prediction,
        game: Game,
        home_team: Team,
        away_team: Team,
    ) -> dict:
        probability = selected_side_probability(
            prediction.simulation_probability, market=prediction.market,
            selection=prediction.selection, model_version=prediction.model_version,
        )
        edge = describe_edge(
            prediction.projected_edge, market=prediction.market,
            selection=prediction.selection, model_version=prediction.model_version,
        )
        return {
            "prediction_id": prediction.id,
            "game_id": game.id,
            "sport": game.sport,
            "home_team": home_team.name,
            "away_team": away_team.name,
            "game_date": _utc_iso(game.game_date),
            "market": parse_market(prediction.market) or "unavailable",
            "selection": parse_selection(prediction.selection) if supported_metadata(
                prediction.market, prediction.selection,
            ) else "unavailable",
            "display_selection": self._display_selection(
                prediction,
                home_team,
                away_team,
            ),
            "line_value": finite_metric(prediction.line_value),
            "american_odds": historical_price(prediction.american_odds),
            "sportsbook": historical_text(prediction.sportsbook),
            "odds_observed_at": _utc_iso(prediction.odds_observed_at),
            "model_version": historical_text(prediction.model_version, fallback="unknown"),
            "npi_score": finite_metric(prediction.npi_score),
            "confidence_score": finite_metric(prediction.confidence_score),
            "simulation_probability": probability,
            "projected_edge": finite_metric(prediction.projected_edge),
            "selected_side_edge": edge.selected_side_value,
            "edge_unit": edge.unit,
            "edge_benchmark": edge.benchmark,
            "risk_level": historical_text(prediction.risk_level),
            "reasoning": metric_reasoning(historical_text(prediction.reasoning), probability),
            "recommendation_eligible": actionable_prediction(prediction) and is_recommendation_eligible(
                prediction.market,
                prediction.american_odds,
            ),
            "recommendation_tier": moneyline_price_tier(
                prediction.market,
                prediction.american_odds,
            ),
            "recommendation_designation": recommendation_designation(
                prediction.market,
                prediction.american_odds,
            ),
        }

    def _display_selection(
        self,
        prediction: Prediction,
        home_team: Team,
        away_team: Team,
    ) -> str:
        market = parse_market(prediction.market)
        selection = parse_selection(prediction.selection)
        if not supported_metadata(market, selection):
            return "Selection unavailable"
        if selection == "PASS":
            return "PASS"
        if market == "spread":
            team = home_team if selection == "HOME" else away_team
            line = finite_metric(prediction.line_value)
            if line is None:
                return team.name
            return f"{team.name} {line:+g}"
        if market == "moneyline":
            team = home_team if selection == "HOME" else away_team
            return f"{team.name} ML"
        if market == "total":
            line = finite_metric(prediction.line_value)
            if line is None:
                return selection
            return f"{selection} {line:g}"
        return "Selection unavailable"
