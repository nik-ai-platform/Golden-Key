from app.core.exceptions import PredictionException
from app.models.prediction.nba_model import NBAPredictionModel
from app.models.prediction.nfl_model import NFLPredictionModel
from app.models.prediction.wnba_model import WNBAPredictionModel


class ModelRegistry:
    """Single source of truth for sport-to-model resolution."""

    def __init__(
        self,
        model_map: dict[str, object] | None = None,
    ):
        if model_map is None:
            model_map = {
                "basketball_nba": NBAPredictionModel(),
                "nba": NBAPredictionModel(),
                "basketball_wnba": WNBAPredictionModel(),
                "wnba": WNBAPredictionModel(),
                "americanfootball_nfl": NFLPredictionModel(),
                "nfl": NFLPredictionModel(),
            }

        self._model_map = {
            self._normalize_key(key): model
            for key, model in model_map.items()
        }

        self._versioned_models: dict[str, dict[str, object]] = {}
        self._active_versions: dict[str, str] = {}

        for sport, model in self._model_map.items():
            version = self._extract_version(model)
            self._versioned_models.setdefault(sport, {})[version] = model
            self._active_versions[sport] = version

    def register(self, sport: str, model) -> None:
        normalized_sport = self._normalize_key(sport)
        self._model_map[normalized_sport] = model

        version = self._extract_version(model)
        self._versioned_models.setdefault(normalized_sport, {})[version] = model
        self._active_versions[normalized_sport] = version

    def register_version(self, sport: str, version: str, model) -> None:
        normalized_sport = self._normalize_key(sport)
        normalized_version = self._normalize_key(version)

        if not normalized_version:
            raise PredictionException("Model version cannot be empty")

        self._versioned_models.setdefault(normalized_sport, {})[
            normalized_version
        ] = model

        if normalized_sport not in self._model_map:
            self._model_map[normalized_sport] = model
            self._active_versions[normalized_sport] = normalized_version

    def set_active_version(self, sport: str, version: str) -> None:
        normalized_sport = self._normalize_key(sport)
        normalized_version = self._normalize_key(version)

        models_for_sport = self._versioned_models.get(normalized_sport, {})
        model = models_for_sport.get(normalized_version)
        if model is None:
            available = ", ".join(sorted(models_for_sport.keys())) or "none"
            raise PredictionException(
                f"Unsupported model version '{version}' for sport '{sport}'. "
                f"Available versions: {available}"
            )

        self._active_versions[normalized_sport] = normalized_version
        self._model_map[normalized_sport] = model

    def get_active_version(self, sport: str) -> str:
        key = self._normalize_key(sport)
        version = self._active_versions.get(key)
        if version is None:
            supported = ", ".join(sorted(self._model_map.keys()))
            raise PredictionException(
                f"Unsupported sport '{sport}'. Supported sports: {supported}"
            )
        return version

    def list_versions(self, sport: str) -> list[str]:
        key = self._normalize_key(sport)
        versions = self._versioned_models.get(key)
        if not versions:
            supported = ", ".join(sorted(self._model_map.keys()))
            raise PredictionException(
                f"Unsupported sport '{sport}'. Supported sports: {supported}"
            )
        return sorted(versions.keys())

    def get_model(self, sport: str, version: str | None = None):
        key = self._normalize_key(sport)

        if version is None:
            model = self._model_map.get(key)
        else:
            model = self._versioned_models.get(key, {}).get(
                self._normalize_key(version)
            )

        if model is None:
            supported = ", ".join(sorted(self._model_map.keys()))
            raise PredictionException(
                f"Unsupported sport '{sport}'. Supported sports: {supported}"
            )
        return model

    def supported_sports(self) -> list[str]:
        return sorted(self._model_map.keys())

    def _normalize_key(self, sport: str) -> str:
        return (sport or "").strip().lower()

    def _extract_version(self, model) -> str:
        metadata = getattr(model, "metadata", None)
        if callable(metadata):
            payload = metadata() or {}
            if payload.get("version"):
                return self._normalize_key(str(payload["version"]))

        model_version = getattr(model, "MODEL_VERSION", None)
        if model_version:
            return self._normalize_key(str(model_version))

        return "unknown"
