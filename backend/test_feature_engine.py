import unittest

from app.services.feature_engine import FeatureEngine


class TestFeatureEngine(unittest.TestCase):
    def setUp(self):
        self.engine = FeatureEngine()

    def test_american_to_probability_negative_odds(self):
        self.assertEqual(self.engine.american_to_probability(-150), 0.6)

    def test_american_to_probability_positive_odds(self):
        self.assertEqual(self.engine.american_to_probability(200), 0.3333)

    def test_american_to_probability_none(self):
        self.assertIsNone(self.engine.american_to_probability(None))

    def test_calculate_moneyline_features(self):
        result = self.engine.calculate_moneyline_features(-130, 110)

        self.assertEqual(result["implied_home_probability"], 0.5652)
        self.assertEqual(result["implied_away_probability"], 0.4762)
        self.assertTrue(result["favorite_is_home"])

    def test_calculate_line_movement(self):
        self.assertEqual(self.engine.calculate_line_movement(-3.5, -2.0), 1.5)

    def test_calculate_line_movement_none(self):
        self.assertIsNone(self.engine.calculate_line_movement(None, -2.0))
        self.assertIsNone(self.engine.calculate_line_movement(-3.5, None))


if __name__ == "__main__":
    unittest.main()
