class ModelVersionService:
    """
    Provides the active prediction model version.
    """

    CURRENT_VERSION = "NPI-v1"
    SPORT_VERSIONS: dict[str, str] = {}
    SPORT_VERSION_HISTORY: dict[str, list[str]] = {}

    def __init__(self):
        pass

    def get_current_version(self) -> str:
        return self.CURRENT_VERSION

    def set_current_version(self, version: str):
        self.CURRENT_VERSION = version

    def get_version_for_sport(self, sport: str, default: str | None = None) -> str:
        key = (sport or "").strip().lower()
        if key in self.SPORT_VERSIONS:
            return self.SPORT_VERSIONS[key]
        if default is not None:
            return default
        return self.CURRENT_VERSION

    def set_version_for_sport(self, sport: str, version: str):
        key = (sport or "").strip().lower()
        previous = self.SPORT_VERSIONS.get(key)
        if previous and previous != version:
            self.SPORT_VERSION_HISTORY.setdefault(key, []).append(previous)
        self.SPORT_VERSIONS[key] = version

    def clear_version_for_sport(self, sport: str):
        key = (sport or "").strip().lower()
        self.SPORT_VERSIONS.pop(key, None)
        self.SPORT_VERSION_HISTORY.pop(key, None)

    def rollback_version_for_sport(self, sport: str) -> str:
        key = (sport or "").strip().lower()
        history = self.SPORT_VERSION_HISTORY.get(key, [])
        if not history:
            return self.get_version_for_sport(sport)

        previous = history.pop()
        self.SPORT_VERSIONS[key] = previous
        if not history:
            self.SPORT_VERSION_HISTORY.pop(key, None)
        return previous
