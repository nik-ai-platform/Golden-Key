import pytest
import requests

from app.core.config import settings


def test_odds_api_sports_smoke():
	api_key = settings.ODDS_API_KEY
	if not api_key:
		pytest.skip("ODDS_API_KEY is not configured")

	response = requests.get(
		"https://api.the-odds-api.com/v4/sports",
		params={"apiKey": api_key},
		timeout=15,
	)
	response.raise_for_status()
	payload = response.json()

	assert isinstance(payload, list)
