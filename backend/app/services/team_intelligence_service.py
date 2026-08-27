from sqlalchemy.orm import Session
from statistics import pstdev

from app.core.constants import DEFAULT_SCORE
from app.repositories import analytics_repository
from app.repositories import prediction_repository
from app.repositories import team_repository
from app.schemas.team_intelligence import TeamIntelligence
from app.services.cache_service import cache_service
from app.services.historical_performance_service import (
    HistoricalPerformanceService
)


class TeamIntelligenceService:
    """
    Builds a reusable intelligence profile for a team by combining existing
    historical, snapshot, team, and analytics inputs.
    """


    def __init__(
        self,
        historical_service=None,
        team_repo=None,
        analytics_repo=None,
        prediction_repo=None,
    ):
        self.historical_service = (
            historical_service or HistoricalPerformanceService()
        )
        self.team_repo = team_repo or team_repository
        self.analytics_repo = analytics_repo or analytics_repository
        self.prediction_repo = prediction_repo or prediction_repository


    def _format_record(
        self,
        wins: int,
        losses: int
    ):
        return f"{wins}-{losses}"


    def _trend_label(
        self,
        trend_value
    ):
        if trend_value is None:
            return "flat"

        if trend_value >= 60:
            return "up"

        if trend_value <= 40:
            return "down"

        return "flat"


    def _split_summary(
        self,
        games,
        team_id: int
    ):
        results = []
        home_games = 0
        away_games = 0
        home_wins = 0
        away_wins = 0

        for game in games:
            result = self.historical_service.calculate_game_result(
                game,
                team_id
            )

            if not result:
                continue

            is_home = game.home_team_id == team_id
            result["is_home"] = is_home
            results.append(result)

            if is_home:
                home_games += 1
                if result["won"]:
                    home_wins += 1
            else:
                away_games += 1
                if result["won"]:
                    away_wins += 1

        home_losses = home_games - home_wins
        away_losses = away_games - away_wins

        average_margin = 0
        if results:
            average_margin = self.historical_service.calculate_average(
                [
                    result["points_for"] - result["points_against"]
                    for result in results
                ]
            )

        total_wins = home_wins + away_wins
        total_games = len(results)
        last10 = self._format_record(
            total_wins,
            total_games - total_wins
        )

        home_win_pct = self.historical_service.calculate_win_rate(
            home_wins,
            home_games
        )

        away_win_pct = self.historical_service.calculate_win_rate(
            away_wins,
            away_games
        )

        strength_score = self.historical_service.calculate_trend(
            [
                result["points_for"] - result["points_against"]
                for result in results[:3]
            ]
        )

        return {
            "results": results,
            "home_record": self._format_record(home_wins, home_losses),
            "away_record": self._format_record(away_wins, away_losses),
            "home_win_pct": home_win_pct,
            "away_win_pct": away_win_pct,
            "last10": last10,
            "average_margin": average_margin,
            "momentum": self.historical_service.calculate_win_rate(
                total_wins,
                total_games
            ),
            "strength": strength_score,
            "consistency": round(
                100 - abs(home_win_pct - away_win_pct),
                2
            ) if total_games else 0,
        }


    def _calculate_momentum(
        self,
        record_summary,
    ):
        record_summary = record_summary or {}

        results = record_summary.get("results") or []

        if results:
            wins = sum(1 for result in results if result.get("won"))
            return round((wins / 10) * 100, 2)

        last10 = record_summary.get("last10")
        if last10 and "-" in last10:
            wins_text = last10.split("-", 1)[0]
            if wins_text.isdigit():
                return round((int(wins_text) / 10) * 100, 2)

        return DEFAULT_SCORE


    def _calculate_consistency(
        self,
        record_summary
    ):
        record_summary = record_summary or {}

        results = record_summary.get("results") or []
        margins = [
            result["points_for"] - result["points_against"]
            for result in results
            if "points_for" in result and "points_against" in result
        ]

        if margins:
            average_margin = self.historical_service.calculate_average(margins)
            margin_spread = round(pstdev(margins), 2) if len(margins) > 1 else 0

            return round(average_margin + margin_spread, 2)

        return record_summary.get(
            "consistency",
            DEFAULT_SCORE
        )


    def _calculate_home_record(
        self,
        record_summary
    ):
        record_summary = record_summary or {}

        return record_summary.get(
            "home_record",
            self._format_record(0, 0)
        )


    def _calculate_away_record(
        self,
        record_summary
    ):
        record_summary = record_summary or {}

        return record_summary.get(
            "away_record",
            self._format_record(0, 0)
        )


    def _calculate_average_margin(
        self,
        record_summary
    ):
        record_summary = record_summary or {}

        return record_summary.get(
            "average_margin",
            0
        )


    def _calculate_trend(
        self,
        record_summary,
        historical_profile
    ):
        record_summary = record_summary or {}
        historical_profile = historical_profile or {}

        trend_value = record_summary.get(
            "strength",
            historical_profile.get("trend", DEFAULT_SCORE)
        )

        return trend_value, self._trend_label(trend_value)


    def build_team_intelligence(
        self,
        team,
        historical_profile,
        *,
        record_summary=None,
        prediction_snapshot=None,
        analytics=None,
    ):
        historical_profile = historical_profile or {}
        record_summary = record_summary or {}

        performance = getattr(team, "performance", None) if team else None

        offense = historical_profile.get("scoring_average", DEFAULT_SCORE)
        defense = historical_profile.get("defense_average", DEFAULT_SCORE)

        if performance:
            if getattr(performance, "offensive_rating", None) is not None:
                offense = performance.offensive_rating
            if getattr(performance, "defensive_rating", None) is not None:
                defense = performance.defensive_rating
        elif analytics:
            implied_home = getattr(analytics, "implied_home_probability", None)
            implied_away = getattr(analytics, "implied_away_probability", None)

            if implied_home is not None:
                offense = round(implied_home * 100, 2)
            elif implied_away is not None:
                offense = round(implied_away * 100, 2)

        momentum = self._calculate_momentum(record_summary)
        consistency = self._calculate_consistency(record_summary)
        home_record = self._calculate_home_record(record_summary)
        away_record = self._calculate_away_record(record_summary)
        average_margin = self._calculate_average_margin(record_summary)
        trend_value, trend_label = self._calculate_trend(
            record_summary,
            historical_profile,
        )

        team_id = getattr(team, "id", 0) if team else 0
        team_name = getattr(team, "name", "") if team else ""

        return TeamIntelligence(
            team_id=team_id,
            team_name=team_name,
            momentum=momentum,
            consistency=consistency,
            trend=trend_label,
            home_win_pct=record_summary.get("home_win_pct", DEFAULT_SCORE),
            away_win_pct=record_summary.get("away_win_pct", DEFAULT_SCORE),
            average_margin=average_margin,
            offensive_rating=offense,
            defensive_rating=defense,
            strength_rating=trend_value,
        )


    def _load_profile_context(
        self,
        db: Session,
        team_id: int
    ):
        team = self.team_repo.get_team(
            db,
            team_id
        )

        games = self.historical_service.get_recent_games(
            db,
            team_id,
            10
        )

        historical_profile = self.historical_service.build_team_profile(
            games,
            team_id
        )

        last_five_profile = self.historical_service.build_team_profile(
            games[:5],
            team_id
        )

        last_five_summary = self._split_summary(
            games[:5],
            team_id
        )

        record_summary = self._split_summary(
            games,
            team_id
        )

        latest_game = games[0] if games else None
        prediction_snapshot = None
        analytics = None

        if latest_game:
            prediction_snapshot = self.prediction_repo.get_latest_snapshot_for_game(
                db,
                latest_game.id
            )

            analytics = self.analytics_repo.get_by_game(
                db,
                latest_game.id
            )

            if prediction_snapshot and not analytics:
                analytics = self.analytics_repo.get_by_game(
                    db,
                    prediction_snapshot.game_id
                )

        return {
            "team": team,
            "games": games,
            "historical_profile": historical_profile,
            "last_five_profile": last_five_profile,
            "last_five_summary": last_five_summary,
            "record_summary": record_summary,
            "prediction_snapshot": prediction_snapshot,
            "analytics": analytics,
        }


    def build_profile(
        self,
        db: Session,
        team_id: int
    ) -> TeamIntelligence:
        cache_key = f"team-intelligence:profile:{team_id}"

        return cache_service.get_or_set(
            cache_key,
            lambda: self._build_profile_uncached(db, team_id),
            ttl_seconds=120,
        )


    def _build_profile_uncached(
        self,
        db: Session,
        team_id: int,
    ) -> TeamIntelligence:
        context = self._load_profile_context(db, team_id)
        return self.build_team_intelligence(
            context["team"],
            context["historical_profile"],
            record_summary=context["record_summary"],
            prediction_snapshot=context["prediction_snapshot"],
            analytics=context["analytics"],
        )


    def get_team_intelligence(
        self,
        db: Session,
        team_id: int
    ):
        cache_key = f"team-intelligence:detail:{team_id}"
        return cache_service.get_or_set(
            cache_key,
            lambda: self._get_team_intelligence_uncached(db, team_id),
            ttl_seconds=120,
        )


    def _get_team_intelligence_uncached(
        self,
        db: Session,
        team_id: int,
    ):
        context = self._load_profile_context(db, team_id)

        profile = self.build_team_intelligence(
            context["team"],
            context["historical_profile"],
            record_summary=context["record_summary"],
            prediction_snapshot=context["prediction_snapshot"],
            analytics=context["analytics"],
        )

        intelligence_data = profile.model_dump()

        return {
            **intelligence_data,
            "team_name": intelligence_data["team_name"] or (context["team"].name if context["team"] else ""),
            "win_percentage": context["historical_profile"].get(
                "win_rate",
                DEFAULT_SCORE
            ),
            "home_record": context["record_summary"]["home_record"],
            "away_record": context["record_summary"]["away_record"],
            "last_5_games": context["last_five_profile"],
            "last_10_games": context["historical_profile"],
            "record": context["record_summary"]["last10"],
            "last10": context["record_summary"]["last10"],
            "last5": context["last_five_summary"]["last10"],
            "strength_trend": intelligence_data["strength_rating"],
            "average_scoring_margin": intelligence_data["average_margin"],
            "offensive_trends": {
                "last_5": context["last_five_profile"].get("scoring_average", DEFAULT_SCORE),
                "last_10": context["historical_profile"].get("scoring_average", DEFAULT_SCORE),
            },
            "defensive_trends": {
                "last_5": context["last_five_profile"].get("defense_average", DEFAULT_SCORE),
                "last_10": context["historical_profile"].get("defense_average", DEFAULT_SCORE),
            },
        }


    def get_dashboard_summary(
        self,
        db: Session,
        team_id: int
    ):
        intelligence = self.get_team_intelligence(
            db,
            team_id
        )

        return {
            "team": intelligence["team_name"],
            "record": intelligence["record"],
            "last10": intelligence["last10"],
            "offense": intelligence["offensive_rating"],
            "defense": intelligence["defensive_rating"],
            "momentum": intelligence["momentum"],
            "strength": intelligence["strength_rating"],
        }
