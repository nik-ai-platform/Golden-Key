from collections import defaultdict
from datetime import datetime, timedelta

from app.core.constants import MAX_SCORE
from app.repositories import analytics_repository
from app.repositories import team_repository
from app.schemas.historical_trends import (
    HistoricalTrendResponse,
    ModelTrendPoint,
    SportTrendPoint,
    TrendPoint,
    TeamTrendResponse,
    TeamTrendWindow,
)


class HistoricalTrendService:
    """
    Analytics-only service for confidence and accuracy trends over time.
    """


    def __init__(
        self,
        analytics_repo=None,
        team_repo=None,
    ):
        self.analytics_repo = analytics_repo or analytics_repository
        self.team_repo = team_repo or team_repository


    def _trend_response(
        self,
        rows,
    ) -> HistoricalTrendResponse:
        return HistoricalTrendResponse(
            daily=self._aggregate(rows, period="daily", include_correct=True),
            weekly=self._aggregate(rows, period="weekly", include_correct=True),
            monthly=self._aggregate(rows, period="monthly", include_correct=True),
        )


    def _period_key(
        self,
        game_date,
        period: str,
    ):
        if game_date is None:
            return "unknown"

        if isinstance(game_date, str):
            game_date = datetime.fromisoformat(game_date)

        if period == "daily":
            return game_date.strftime("%Y-%m-%d")

        if period == "weekly":
            iso_year, iso_week, _ = game_date.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"

        return game_date.strftime("%Y-%m")


    def _group_rows(
        self,
        rows,
        *,
        period: str,
    ):
        buckets = defaultdict(list)

        for row in rows:
            key = self._period_key(row[0], period)
            buckets[key].append(row)

        return buckets


    def _aggregate(
        self,
        rows,
        *,
        period: str,
        include_correct: bool = False,
    ) -> list[TrendPoint]:
        buckets = self._group_rows(rows, period=period)

        points = []

        for key in sorted(buckets.keys()):
            values = buckets[key]

            predictions = len(values)
            correct = sum(1 for value in values if value[1])

            confidences = [
                value[2]
                for value in values
                if value[2] is not None
            ]

            average_confidence = 0
            if confidences:
                average_confidence = round(
                    sum(confidences) / len(confidences),
                    2,
                )

            points.append(
                TrendPoint(
                    period=key,
                    accuracy=round(
                        correct / predictions * MAX_SCORE,
                        2,
                    ) if predictions else 0,
                    confidence=average_confidence,
                    predictions=predictions,
                    correct=correct if include_correct else None,
                )
            )

        return points


    def _filter_rows(
        self,
        db,
        *,
        team_id: int | None = None,
        sport: str | None = None,
        version: str | None = None,
    ):
        return self.analytics_repo.get_evaluation_trend_rows(
            db,
            team_id=team_id,
            sport=sport,
            version=version,
        )


    def _window_rows(
        self,
        rows,
        days: int = 30,
    ):
        if not rows:
            return []

        dates = [row[0] for row in rows if row[0] is not None]
        if not dates:
            return []

        cutoff = max(dates) - timedelta(days=days)
        return [row for row in rows if row[0] is not None and row[0] >= cutoff]


    def _accuracy_and_momentum(
        self,
        rows,
    ):
        if not rows:
            return TeamTrendWindow(accuracy=0, momentum=0)

        predictions = len(rows)
        correct = sum(1 for row in rows if row[1])
        confidences = [row[2] for row in rows if row[2] is not None]

        momentum = 0
        if confidences:
            momentum = round(sum(confidences) / len(confidences), 2)

        return TeamTrendWindow(
            accuracy=round(correct / predictions * MAX_SCORE, 2),
            momentum=momentum,
        )


    def _named_entity_trends(
        self,
        rows,
        *,
        key_index: int,
        field_name: str,
        value_model,
    ):
        grouped = defaultdict(list)

        for row in rows:
            grouped[row[key_index]].append(row)

        output = []

        for key in sorted(grouped.keys()):
            values = grouped[key]
            predictions = len(values)
            correct = sum(1 for row in values if row[1])

            output.append(
                value_model(
                    **{
                        field_name: key,
                        "accuracy": round(
                            correct / predictions * MAX_SCORE,
                            2,
                        ) if predictions else 0,
                    }
                )
            )

        return output


    def daily_trends(
        self,
        db,
    ):
        rows = self._filter_rows(db)
        return self._aggregate(rows, period="daily", include_correct=True)


    def weekly_trends(
        self,
        db,
    ):
        rows = self._filter_rows(db)
        return self._aggregate(rows, period="weekly", include_correct=True)


    def monthly_trends(
        self,
        db,
    ):
        rows = self._filter_rows(db)
        return self._aggregate(rows, period="monthly", include_correct=True)


    def daily_accuracy(
        self,
        db,
    ):
        return self.daily_trends(db)


    def weekly_accuracy(
        self,
        db,
    ):
        return self.weekly_trends(db)


    def monthly_accuracy(
        self,
        db,
    ):
        return self.monthly_trends(db)


    def team_trends(
        self,
        db,
        team_id,
    ):
        team = self.team_repo.get_team(db, team_id)
        rows = self._filter_rows(
            db,
            team_id=team_id,
        )
        last30_rows = self._window_rows(rows, days=30)

        return TeamTrendResponse(
            team=(team.name if team else ""),
            last30=self._accuracy_and_momentum(last30_rows),
        )


    def sport_trends(
        self,
        db,
        sport=None,
    ):
        rows = self._filter_rows(
            db,
            sport=sport,
        )

        return self._named_entity_trends(
            rows,
            key_index=5,
            field_name="sport",
            value_model=SportTrendPoint,
        )


    def model_trends(
        self,
        db,
        version=None,
    ):
        rows = self._filter_rows(
            db,
            version=version,
        )

        return self._named_entity_trends(
            rows,
            key_index=6,
            field_name="version",
            value_model=ModelTrendPoint,
        )