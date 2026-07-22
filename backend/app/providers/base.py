from abc import ABC, abstractmethod


class SportsDataProvider(ABC):
    """
    Base interface for all sports data providers.
    """

    @abstractmethod
    def get_games(self, sport: str):
        """Return today's games."""
        raise NotImplementedError

    @abstractmethod
    def get_odds(self, sport: str):
        """Return current betting odds."""
        raise NotImplementedError

    @abstractmethod
    def get_scores(self, sport: str):
        """Return live/final scores."""
        raise NotImplementedError
