import os

import requests


class SportsDataClient:

    def __init__(self):

        self.api_key = os.getenv("SPORTS_API_KEY")

        self.base_url = os.getenv("SPORTS_API_URL")

    def get_games(
        self,
        sport: str,
    ):

        if not self.base_url:
            raise ValueError("SPORTS_API_URL is not configured")

        response = requests.get(
            f"{self.base_url}/games",
            headers={
                "Authorization": self.api_key,
            },
            params={
                "sport": sport,
            },
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    def get_odds(
        self,
        sport: str,
    ):

        if not self.base_url:
            raise ValueError("SPORTS_API_URL is not configured")

        response = requests.get(
            f"{self.base_url}/odds",
            headers={
                "Authorization": self.api_key,
            },
            params={
                "sport": sport,
            },
            timeout=15,
        )

        response.raise_for_status()

        return response.json()