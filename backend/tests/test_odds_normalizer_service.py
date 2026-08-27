from app.services.odds_normalizer_service import OddsNormalizerService


def test_normalizes_spread_moneyline_total():
    service = OddsNormalizerService()
    game = {
        "home_team": "Boston Celtics",
        "away_team": "New York Knicks",
    }
    bookmaker = {
        "key": "test_book",
        "title": "Test Book",
        "markets": [
            {
                "key": "spreads",
                "outcomes": [
                    {
                        "name": "Boston Celtics",
                        "point": -4.5,
                        "price": -110,
                    },
                    {
                        "name": "New York Knicks",
                        "point": 4.5,
                        "price": -110,
                    },
                ],
            },
            {
                "key": "h2h",
                "outcomes": [
                    {"name": "Boston Celtics", "price": -180},
                    {"name": "New York Knicks", "price": 155},
                ],
            },
            {
                "key": "totals",
                "outcomes": [
                    {"name": "Over", "point": 224.5, "price": -110},
                    {"name": "Under", "point": 224.5, "price": -110},
                ],
            },
        ],
    }

    result = service.normalize_bookmaker(game, bookmaker)

    assert result["spread_home"] == -4.5
    assert result["spread_away"] == 4.5
    assert result["moneyline_home"] == -180
    assert result["moneyline_away"] == 155
    assert result["total"] == 224.5
