from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, aliased

from app.models.game import Game
from app.models.odds import Odds
from app.models.prediction_record import Prediction
from app.models.team import Team
from app.services.recommendation_eligibility import (
    LOWER_PRIORITY,
    is_recommendation_eligible,
    moneyline_price_tier,
)


class ParlayOptimizationError(ValueError):
    pass


class ParlayOptimizerService:
    SUPPORTED_LEG_COUNTS = {2, 4, 6, 8, 10}
    MAX_GAME_HORIZON_DAYS = 7
    MAX_ODDS_AGE = timedelta(hours=6)
    MIN_PROJECTED_EDGE = 1.0
    BEAM_WIDTH = 500
    MARKET_MIX_RULES = {
        2: {"max_moneylines": 1, "min_spreads": 0, "min_totals": 0},
        4: {"max_moneylines": 2, "min_spreads": 1, "min_totals": 1},
        6: {"max_moneylines": 2, "min_spreads": 2, "min_totals": 1},
        8: {"max_moneylines": 3, "min_spreads": 2, "min_totals": 2},
        10: {"max_moneylines": 3, "min_spreads": 3, "min_totals": 2},
    }

    def build_parlay(
        self,
        db: Session,
        *,
        leg_count: int,
        sport: str | None = None,
    ) -> dict:
        if leg_count not in self.SUPPORTED_LEG_COUNTS:
            raise ValueError("Leg count must be one of 2, 4, 6, 8, or 10")

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        horizon_end = now + timedelta(days=self.MAX_GAME_HORIZON_DAYS)
        candidates = self._load_candidates(
            db,
            sport=sport,
            now=now,
            horizon_end=horizon_end,
        )
        if len({item["game_id"] for item in candidates}) < leg_count:
            article = "an" if leg_count == 8 else "a"
            raise ParlayOptimizationError(
                "Not enough qualified predictions to build "
                f"{article} {leg_count}-leg optimized parlay."
            )

        legs = self._optimize(candidates, leg_count)
        if legs is None:
            raise ValueError(
                "Qualified predictions cannot satisfy the requested market mix"
            )

        market_mix = {
            market: sum(item["market"] == market for item in legs)
            for market in ("spread", "total", "moneyline")
        }
        return {
            "leg_count": leg_count,
            "generated_at": now,
            "horizon_days": self.MAX_GAME_HORIZON_DAYS,
            "sport": sport.upper() if sport else None,
            "legs": legs,
            "average_npi": self._average(legs, "npi_score"),
            "average_confidence": self._average(legs, "confidence_score"),
            "average_projected_edge": self._average(legs, "projected_edge"),
            "combined_american_odds": self._combined_american_odds(legs),
            "risk_level": self._parlay_risk(legs),
            "market_mix": market_mix,
        }

    def _load_candidates(
        self,
        db: Session,
        sport: str | None,
        now: datetime,
        horizon_end: datetime,
    ) -> list[dict]:
        cutoff = now - self.MAX_ODDS_AGE
        home_team = aliased(Team)
        away_team = aliased(Team)
        query = (
            db.query(Prediction, Game, Odds, home_team, away_team)
            .join(Game, Game.id == Prediction.game_id)
            .join(Odds, Odds.id == Prediction.odds_snapshot_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
            .filter(
                Game.game_date >= now,
                Game.game_date <= horizon_end,
                Game.status != "final",
                Prediction.market.in_(("spread", "moneyline", "total")),
                Prediction.selection != "PASS",
                Prediction.odds_snapshot_id.is_not(None),
                Prediction.sportsbook.is_not(None),
                Prediction.odds_observed_at.is_not(None),
                Prediction.odds_observed_at >= cutoff,
                Prediction.projected_edge.is_not(None),
                Prediction.projected_edge >= self.MIN_PROJECTED_EDGE,
                Prediction.american_odds.is_not(None),
                Odds.game_id == Prediction.game_id,
                Odds.sportsbook == Prediction.sportsbook,
                Odds.created_at == Prediction.odds_observed_at,
            )
        )
        if sport:
            query = query.filter(Game.sport == sport.upper())

        candidates = []
        for prediction, game, odds, home, away in query.all():
            if not is_recommendation_eligible(
                prediction.market,
                prediction.american_odds,
            ):
                continue
            if game.game_date < now:
                continue
            if game.game_date > horizon_end:
                continue
            if prediction.game_id != game.id:
                continue
            if prediction.odds_snapshot_id is None:
                continue
            if odds.game_id != prediction.game_id:
                continue
            if prediction.market == "moneyline" and prediction.american_odds is None:
                continue
            if prediction.market in {"spread", "total"} and prediction.line_value is None:
                continue
            score, components = self._score(prediction, now)
            candidates.append(
                {
                    "prediction_id": prediction.id,
                    "game_id": game.id,
                    "sport": game.sport,
                    "game_date": game.game_date.isoformat(),
                    "home_team": home.name,
                    "away_team": away.name,
                    "market": prediction.market,
                    "selection": prediction.selection,
                    "display_selection": self._display_selection(
                        prediction,
                        home.name,
                        away.name,
                    ),
                    "line_value": prediction.line_value,
                    "american_odds": prediction.american_odds,
                    "npi_score": round(float(prediction.npi_score), 2),
                    "confidence_score": round(
                        float(prediction.confidence_score or 0), 2
                    ),
                    "simulation_probability": round(
                        float(prediction.simulation_probability or 0), 2
                    ),
                    "projected_edge": round(float(prediction.projected_edge), 2),
                    "risk_level": (prediction.risk_level or "MEDIUM").upper(),
                    "parlay_score": score,
                    "score_components": components,
                    "reasoning": prediction.reasoning,
                    "odds_snapshot_id": prediction.odds_snapshot_id,
                    "sportsbook": prediction.sportsbook,
                    "odds_observed_at": prediction.odds_observed_at.isoformat(),
                }
            )
        return sorted(
            candidates,
            key=lambda item: (-item["parlay_score"], item["prediction_id"]),
        )

    def _score(self, prediction: Prediction, now: datetime) -> tuple[float, dict]:
        age = max(
            0.0,
            (now - prediction.odds_observed_at).total_seconds(),
        )
        max_age = self.MAX_ODDS_AGE.total_seconds()
        risk_points = {
            "LOW": 10.0,
            "MEDIUM": 6.0,
            "MODERATE": 6.0,
            "HIGH": 2.0,
        }.get((prediction.risk_level or "MEDIUM").upper(), 5.0)
        components = {
            "npi_strength": self._scaled(prediction.npi_score, 200, 25),
            "confidence": self._scaled(prediction.confidence_score, 100, 25),
            "simulation_probability": self._scaled(
                prediction.simulation_probability,
                100,
                15,
            ),
            "projected_edge": self._scaled(prediction.projected_edge, 10, 15),
            "odds_freshness": round(max(0.0, 10 * (1 - age / max_age)), 2),
            "risk_adjustment": risk_points,
            "moneyline_price_adjustment": (
                -0.01
                if moneyline_price_tier(
                    prediction.market,
                    prediction.american_odds,
                ) == LOWER_PRIORITY
                else 0.0
            ),
        }
        return round(sum(components.values()), 2), components

    def _optimize(self, candidates: list[dict], leg_count: int) -> list[dict] | None:
        rules = self.MARKET_MIX_RULES[leg_count]
        states = [([], frozenset(), {"spread": 0, "total": 0, "moneyline": 0}, 0.0)]

        for _ in range(leg_count):
            expanded = {}
            for legs, game_ids, counts, adjusted_score in states:
                for candidate in candidates:
                    if candidate["game_id"] in game_ids:
                        continue
                    market = candidate["market"]

                    new_legs = [*legs, candidate]
                    if not self._partial_market_mix_is_feasible(
                        new_legs,
                        requested_legs=leg_count,
                        **rules,
                    ):
                        continue
                    if len(new_legs) == leg_count and not self._meets_final_market_mix(
                        new_legs,
                        **rules,
                    ):
                        continue

                    key = tuple(sorted(item["prediction_id"] for item in new_legs))
                    repeat_penalty = counts[market] * 1.5
                    if market == "total" and any(
                        item["market"] == "total"
                        and item["selection"] == candidate["selection"]
                        for item in legs
                    ):
                        repeat_penalty += 1.0
                    new_counts = {**counts, market: counts[market] + 1}
                    new_score = adjusted_score + candidate["parlay_score"] - repeat_penalty
                    state = (
                        new_legs,
                        game_ids | {candidate["game_id"]},
                        new_counts,
                        new_score,
                    )
                    previous = expanded.get(key)
                    if previous is None or previous[3] < new_score:
                        expanded[key] = state

            states = sorted(
                expanded.values(),
                key=lambda state: self._state_rank(state, rules),
                reverse=True,
            )[: self.BEAM_WIDTH]
            if not states:
                return None

        valid = [
            state
            for state in states
            if self._meets_final_market_mix(state[0], **rules)
        ]
        if not valid:
            return None
        return sorted(
            max(valid, key=lambda state: state[3])[0],
            key=lambda item: (-item["parlay_score"], item["prediction_id"]),
        )

    @staticmethod
    def _state_rank(state, rules) -> float:
        counts = state[2]
        quota_progress = (
            min(counts["spread"], rules["min_spreads"])
            + min(counts["total"], rules["min_totals"])
        )
        return state[3] + quota_progress * 5

    @staticmethod
    def _partial_market_mix_is_feasible(
        selected: list[dict],
        *,
        requested_legs: int,
        min_spreads: int,
        min_totals: int,
        max_moneylines: int,
    ) -> bool:
        counts = ParlayOptimizerService._market_counts(selected)
        remaining_slots = requested_legs - len(selected)
        needed_spreads = max(0, min_spreads - counts["spread"])
        needed_totals = max(0, min_totals - counts["total"])

        if counts["moneyline"] > max_moneylines:
            return False
        return needed_spreads + needed_totals <= remaining_slots

    @staticmethod
    def _meets_final_market_mix(
        selected: list[dict],
        *,
        min_spreads: int,
        min_totals: int,
        max_moneylines: int,
    ) -> bool:
        counts = ParlayOptimizerService._market_counts(selected)
        return (
            counts["spread"] >= min_spreads
            and counts["total"] >= min_totals
            and counts["moneyline"] <= max_moneylines
        )

    @staticmethod
    def _market_counts(selected: list[dict]) -> dict[str, int]:
        counts = {"spread": 0, "moneyline": 0, "total": 0}
        for candidate in selected:
            counts[candidate["market"]] += 1
        return counts

    @staticmethod
    def _scaled(value, maximum: float, points: float) -> float:
        return round(max(0.0, min(float(value or 0) / maximum, 1.0)) * points, 2)

    @staticmethod
    def _average(legs: list[dict], field: str) -> float:
        return round(sum(float(item[field]) for item in legs) / len(legs), 2)

    @staticmethod
    def _display_selection(prediction: Prediction, home: str, away: str) -> str:
        if prediction.market == "total":
            return f"{away} at {home} {prediction.selection} {prediction.line_value:g}"
        team = home if prediction.selection == "HOME" else away
        if prediction.market == "moneyline":
            return f"{team} ML {prediction.american_odds:+d}"
        return f"{team} {prediction.line_value:+g}"

    @staticmethod
    def _combined_american_odds(legs: list[dict]) -> int:
        decimal_odds = 1.0
        for leg in legs:
            price = leg["american_odds"]
            decimal_odds *= 1 + (price / 100 if price > 0 else 100 / abs(price))
        if decimal_odds >= 2:
            return round((decimal_odds - 1) * 100)
        return round(-100 / (decimal_odds - 1))

    @staticmethod
    def _parlay_risk(legs: list[dict]) -> str:
        high = sum(item["risk_level"] == "HIGH" for item in legs)
        low = sum(item["risk_level"] == "LOW" for item in legs)
        if high >= 2:
            return "HIGH"
        if low == len(legs):
            return "LOW"
        return "MEDIUM"