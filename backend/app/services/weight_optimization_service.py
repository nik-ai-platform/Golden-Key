from __future__ import annotations

from hashlib import sha256
from typing import Any


class WeightOptimizationService:

    TOTAL_WEIGHT = 200.0

    SPORT_BASELINES = {
        "nba": {
            "momentum": 22.0,
            "rest": 12.0,
            "net_rating": 28.0,
            "pace": 18.0,
            "market": 20.0,
        },
        "nfl": {
            "turnover_diff": 32.0,
            "qb_efficiency": 38.0,
            "pressure_rate": 24.0,
            "red_zone": 26.0,
            "market": 18.0,
        },
        "wnba": {
            "momentum": 24.0,
            "rest": 14.0,
            "rotation_stability": 26.0,
            "defense": 24.0,
            "market": 16.0,
        },
    }

    def __init__(self):
        self._profiles: dict[str, dict[str, Any]] = {}

    def generate_candidate_weights(
        self,
        sport,
    ):
        sport_key = self._sport_key(sport)
        base = dict(self.SPORT_BASELINES.get(sport_key, self.SPORT_BASELINES["nba"]))

        # Deterministic tweak: redistribute a small amount based on sport hash.
        keys = sorted(base.keys())
        seed = int(sha256(sport_key.encode("utf-8")).hexdigest()[:8], 16)
        source_index = seed % len(keys)
        target_index = (seed // len(keys)) % len(keys)
        if source_index == target_index:
            target_index = (target_index + 1) % len(keys)

        source_key = keys[source_index]
        target_key = keys[target_index]
        shift = min(4.0, max(1.0, base[source_key] * 0.15))

        base[source_key] = max(0.0, base[source_key] - shift)
        base[target_key] = base[target_key] + shift

        return self.normalize_weights(base)

    def normalize_weights(
        self,
        weights,
    ):
        if not isinstance(weights, dict) or not weights:
            raise ValueError("weights must be a non-empty dictionary")

        normalized_input: dict[str, float] = {}
        for key, value in weights.items():
            if value is None:
                raise ValueError(f"weight for '{key}' cannot be None")

            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"weight for '{key}' must be numeric") from exc

            if numeric < 0:
                raise ValueError(f"weight for '{key}' cannot be negative")

            normalized_input[str(key)] = numeric

        total = sum(normalized_input.values())
        if total <= 0:
            raise ValueError("sum of weights must be greater than zero")

        normalized = {
            key: round((value / total) * self.TOTAL_WEIGHT, 2)
            for key, value in normalized_input.items()
        }

        delta = round(self.TOTAL_WEIGHT - sum(normalized.values()), 2)
        if delta != 0:
            first_key = sorted(normalized.keys())[0]
            normalized[first_key] = round(normalized[first_key] + delta, 2)

        return normalized

    def compare_profiles(
        self,
        current,
        candidate,
    ):
        current_weights = self.normalize_weights(self._extract_weights(current))
        candidate_weights = self.normalize_weights(self._extract_weights(candidate))

        current_metrics = self._extract_metrics(current)
        candidate_metrics = self._extract_metrics(candidate)

        shared_features = sorted(set(current_weights.keys()) | set(candidate_weights.keys()))
        weight_shift = round(
            sum(abs(candidate_weights.get(f, 0.0) - current_weights.get(f, 0.0)) for f in shared_features),
            2,
        )

        return {
            "current_total": round(sum(current_weights.values()), 2),
            "candidate_total": round(sum(candidate_weights.values()), 2),
            "totals_valid": (
                round(sum(current_weights.values()), 2) == self.TOTAL_WEIGHT
                and round(sum(candidate_weights.values()), 2) == self.TOTAL_WEIGHT
            ),
            "features_compared": shared_features,
            "weight_shift": weight_shift,
            "accuracy_delta": round(candidate_metrics["accuracy"] - current_metrics["accuracy"], 2),
            "calibration_delta": round(candidate_metrics["calibration"] - current_metrics["calibration"], 2),
            "roi_delta": round(candidate_metrics["roi"] - current_metrics["roi"], 2),
            "current_metrics": current_metrics,
            "candidate_metrics": candidate_metrics,
        }

    def recommend_profile(
        self,
        comparison,
    ):
        if not comparison.get("totals_valid"):
            return {
                "recommended": "current",
                "reason": "Weight totals must normalize to 200",
            }

        accuracy_up = comparison.get("accuracy_delta", 0.0) > 0
        calibration_not_worse = comparison.get("calibration_delta", 0.0) <= 0
        roi_not_worse = comparison.get("roi_delta", 0.0) >= 0

        if accuracy_up and calibration_not_worse and roi_not_worse:
            return {
                "recommended": "candidate",
                "reason": "Candidate improves accuracy without hurting calibration or ROI",
            }

        return {
            "recommended": "current",
            "reason": "Candidate failed promotion thresholds",
        }

    def set_active_profile(self, sport: str, profile: dict[str, Any]) -> None:
        sport_key = self._sport_key(sport)
        payload = dict(profile)
        payload["weights_json"] = self.normalize_weights(self._extract_weights(profile))

        state = self._profiles.setdefault(sport_key, {"active": None, "candidates": []})
        state["active"] = payload

    def store_candidate_profile(self, sport: str, profile: dict[str, Any]) -> None:
        sport_key = self._sport_key(sport)
        payload = dict(profile)
        payload["weights_json"] = self.normalize_weights(self._extract_weights(profile))

        state = self._profiles.setdefault(sport_key, {"active": None, "candidates": []})
        state["candidates"].append(payload)

    def get_active_profile(self, sport: str) -> dict[str, Any] | None:
        sport_key = self._sport_key(sport)
        return self._profiles.get(sport_key, {}).get("active")

    def get_candidate_profiles(self, sport: str) -> list[dict[str, Any]]:
        sport_key = self._sport_key(sport)
        return list(self._profiles.get(sport_key, {}).get("candidates", []))

    def _extract_weights(self, profile: Any) -> dict[str, float]:
        if isinstance(profile, dict):
            if "weights_json" in profile:
                return profile["weights_json"] or {}
            return profile

        return getattr(profile, "weights_json", {}) or {}

    def _extract_metrics(self, profile: Any) -> dict[str, float]:
        if isinstance(profile, dict):
            metrics = profile.get("metrics", {})
        else:
            metrics = getattr(profile, "metrics", {}) or {}

        return {
            "accuracy": round(float(metrics.get("accuracy", 0.0) or 0.0), 2),
            "calibration": round(float(metrics.get("calibration", 0.0) or 0.0), 2),
            "roi": round(float(metrics.get("roi", 0.0) or 0.0), 2),
        }

    def _sport_key(self, sport: str) -> str:
        return (sport or "unknown").strip().lower()
