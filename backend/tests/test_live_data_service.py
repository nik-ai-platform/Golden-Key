import pytest

from app.services.live_data_service import LiveDataService


@pytest.mark.integration
def test_fetch_games_returns_list():

	service = LiveDataService()

	games = service.fetch_games("baseball_mlb")

	assert isinstance(games, list)


@pytest.mark.integration
def test_fetch_games_contains_expected_fields():

	service = LiveDataService()

	games = service.fetch_games("baseball_mlb")

	# If there are no current games, the API should return an empty list.
	if not games:
		return

	game = games[0]

	required_fields = [
		"id",
		"sport_key",
		"commence_time",
		"home_team",
		"away_team",
		"bookmakers",
	]

	for field in required_fields:
		assert field in game
