class ModelWeightService:
    """
    Stores and retrieves NPI weight configurations.
    """


    DEFAULT_WEIGHTS = {

        "strength": 0.40,

        "recent_form": 0.20,

        "offense_defense": 0.20,

        "historical": 0.00,

        "opponent_strength": 0.00,

        "odds_market": 0.10,

        "situational": 0.10

    }


    def get_weights(self):

        return self.DEFAULT_WEIGHTS
