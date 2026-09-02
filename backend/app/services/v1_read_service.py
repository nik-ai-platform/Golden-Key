from datetime import UTC, date, datetime, timedelta, timezone

from sqlalchemy.orm import Session, aliased

from app.models.game import Game
from app.models.prediction_record import Prediction
from app.models.prediction_result import PredictionResult
from app.models.team import Team
from app.models.user_prediction import UserPrediction


def _utc_iso(value: datetime) -> str:
    """
    Serialize game timestamps as explicit UTC.

    Golden Key stores game_date as naive UTC in Postgres.
    Adding the UTC timezone before serialization prevents browsers
    from interpreting the stored UTC clock time as local time.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)

    return value.isoformat().replace("+00:00", "Z")


class V1ReadService:

    LONG_MONEYLINE_ODDS = 500
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
        query = (
            db.query(Game.game_date)
            .join(Prediction, Prediction.game_id == Game.id)
            .filter(Game.game_date >= now, Game.game_date <= window_end)
            .filter(Game.status != "final")
        )
        if sport:
            query = query.filter(Game.sport == sport.upper())
        if not include_passes:
            query = query.filter(Prediction.selection != "PASS")

        first_game_date = query.order_by(Game.game_date.asc()).limit(1).scalar()
        return first_game_date.date() if first_game_date else today

    def _build_daily_card(self, predictions: list[dict]) -> dict:
        ranked = sorted(
            predictions,
            key=lambda prediction: (
                -self._daily_card_score(prediction),
                -float(prediction.get("confidence_score") or 0),
                -float(prediction.get("projected_edge") or 0),
                prediction["prediction_id"],
            ),
        )
        used_ids = set()
        primary_candidates = [
            prediction
            for prediction in ranked
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
                    for item in ranked
                    if item["market"].lower() == market
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
                for prediction in ranked
                if prediction["prediction_id"] not in used_ids
                and prediction["market"].lower() == "spread"
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
            for prediction in ranked
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
        if confidence is not None:
            reasons.append(f"{float(confidence):.1f}% confidence")
        if edge is not None:
            reasons.append(f"{float(edge):.1f}% projected edge")
        return {
            "role": role,
            "label": label,
            "ranking_score": self._daily_card_score(prediction),
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
            abs(float(prediction.get("projected_edge") or 0)) * 10
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
            prediction["market"].lower() == "moneyline"
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
        home_team = aliased(Team)
        away_team = aliased(Team)
        query = (
            db.query(Prediction, Game, home_team, away_team)
            .join(Game, Game.id == Prediction.game_id)
            .join(home_team, home_team.id == Game.home_team_id)
            .join(away_team, away_team.id == Game.away_team_id)
        )
        if sport:
            query = query.filter(Game.sport == sport.upper())
        if not include_passes:
            query = query.filter(Prediction.selection != "PASS")
        query = query.filter(Game.status != "final")

        rows = query.filter(
            Game.game_date >= max(day_start, now if day_start == today_start else day_start),
            Game.game_date <= day_end,
        ).order_by(
            Prediction.id.desc(),
            Prediction.confidence_score.desc(),
            Prediction.npi_score.desc(),
        ).all()
        latest_by_game_market = {}
        for prediction, game, home, away in rows:
            latest_by_game_market.setdefault(
                (prediction.game_id, prediction.market),
                (prediction, game, home, away),
            )
        items = [
            self._prediction_item(prediction, game, home, away)
            for prediction, game, home, away in latest_by_game_market.values()
        ]
        return {
            "sport": sport.upper() if sport else None,
            "slate_date": slate_date.isoformat(),
            "count": len(items),
            "predictions": items,
        }

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
            .order_by(Prediction.id.desc())
            .all()
        )
        latest_by_market = {}
        for prediction in prediction_rows:
            latest_by_market.setdefault(prediction.market, prediction)
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
                    "market": prediction.market,
                    "selection": prediction.selection,
                    "display_selection": self._display_selection(
                        prediction,
                        home,
                        away,
                    ),
                    "line_value": prediction.line_value,
                    "american_odds": prediction.american_odds,
                    "npi_score": float(prediction.npi_score),
                    "confidence_score": prediction.confidence_score,
                    "risk_level": prediction.risk_level,
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
                    prediction.market.lower()
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
                    "market": prediction.market,
                    "display_selection": self._display_selection(
                        prediction,
                        home,
                        away,
                    ),
                    "npi_score": float(prediction.npi_score),
                    "outcome": result.outcome,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                }
                for result, prediction, game, home, away in rows[:10]
            ],
        }

    def _prediction_item(
        self,
        prediction: Prediction,
        game: Game,
        home_team: Team,
        away_team: Team,
    ) -> dict:
        return {
            "prediction_id": prediction.id,
            "game_id": game.id,
            "sport": game.sport,
            "home_team": home_team.name,
            "away_team": away_team.name,
            "game_date": _utc_iso(game.game_date),
            "market": prediction.market,
            "selection": prediction.selection,
            "display_selection": self._display_selection(
                prediction,
                home_team,
                away_team,
            ),
            "line_value": prediction.line_value,
            "american_odds": prediction.american_odds,
            "model_version": prediction.model_version,
            "npi_score": float(prediction.npi_score),
            "confidence_score": prediction.confidence_score,
            "simulation_probability": prediction.simulation_probability,
            "projected_edge": prediction.projected_edge,
            "risk_level": prediction.risk_level,
            "reasoning": prediction.reasoning,
        }

    def _display_selection(
        self,
        prediction: Prediction,
        home_team: Team,
        away_team: Team,
    ) -> str:
        if prediction.selection == "PASS":
            return "PASS"
        if prediction.market == "spread":
            team = home_team if prediction.selection == "HOME" else away_team
            if prediction.line_value is None:
                return team.name
            return f"{team.name} {prediction.line_value:+g}"
        if prediction.market == "moneyline":
            team = home_team if prediction.selection == "HOME" else away_team
            return f"{team.name} ML"
        if prediction.market == "total":
            if prediction.line_value is None:
                return prediction.selection
            return f"{prediction.selection} {prediction.line_value:g}"
        return prediction.selection
