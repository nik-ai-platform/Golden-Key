from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.feature_snapshot import FeatureSnapshot
from app.models.prediction_snapshot import PredictionSnapshot


class PredictionSnapshotService:

    """
    Stores prediction inputs for future evaluation and model comparison.
    """

    def save_snapshot(
        self,
        db: Session,
        *,
        game_id: int,
        model_version: str,
        prediction: str,
        confidence: float,
        home_score: float,
        away_score: float,
        home_features: dict,
        away_features: dict,
        commit: bool = True,
    ):
        if not self._has_table(db, "prediction_snapshots"):
            return None

        snapshot = PredictionSnapshot(
            game_id=game_id,
            model_version=model_version,
            prediction=prediction,
            confidence=confidence,
            home_score=home_score,
            away_score=away_score,
            home_features=home_features,
            away_features=away_features
        )

        db.add(snapshot)
        if commit:
            db.commit()
            db.refresh(snapshot)

        return snapshot

    def save_feature_snapshots(
        self,
        db: Session,
        *,
        prediction_id: int,
        model_version: str,
        home_features: dict,
        away_features: dict,
        confidence: float,
        commit: bool = True,
    ):
        if not self._has_table(db, "feature_snapshots"):
            return []

        rows = []

        pairs = [
            ("home_strength", self._feature_value(home_features, ("team_strength", "strength", "win_rate"))),
            ("away_strength", self._feature_value(away_features, ("team_strength", "strength", "win_rate"))),
            ("home_momentum", self._feature_value(home_features, ("momentum", "trend"))),
            ("away_momentum", self._feature_value(away_features, ("momentum", "trend"))),
            ("home_offensive_rating", self._feature_value(home_features, ("offensive_rating", "offense", "scoring_average"))),
            ("away_offensive_rating", self._feature_value(away_features, ("offensive_rating", "offense", "scoring_average"))),
            ("home_defensive_rating", self._feature_value(home_features, ("defensive_rating", "defense", "defense_average"))),
            ("away_defensive_rating", self._feature_value(away_features, ("defensive_rating", "defense", "defense_average"))),
            ("home_rest_days", self._feature_value(home_features, ("rest_days",))),
            ("away_rest_days", self._feature_value(away_features, ("rest_days",))),
            ("home_market_odds", self._feature_value(home_features, ("market_odds", "odds", "odds_market"))),
            ("away_market_odds", self._feature_value(away_features, ("market_odds", "odds", "odds_market"))),
            ("home_recent_form", self._feature_value(home_features, ("recent_form", "form"))),
            ("away_recent_form", self._feature_value(away_features, ("recent_form", "form"))),
            ("confidence", float(confidence or 0.0)),
        ]

        for feature_name, feature_value in pairs:
            row = FeatureSnapshot(
                prediction_id=prediction_id,
                feature_name=feature_name,
                feature_value=round(float(feature_value), 4),
                model_version=model_version,
            )
            db.add(row)
            rows.append(row)

        if commit:
            db.commit()
            for row in rows:
                db.refresh(row)

        return rows

    def _feature_value(self, features, aliases):
        payload = features or {}
        for alias in aliases:
            if alias in payload and payload[alias] is not None:
                return float(payload[alias])
        return 50.0

    def _has_table(self, db: Session, table_name: str) -> bool:
        if not hasattr(db, "get_bind"):
            return True
        return inspect(db.get_bind()).has_table(table_name)
