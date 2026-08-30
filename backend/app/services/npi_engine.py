from dataclasses import dataclass

from app.services.npi_weight_profile_service import NPIWeightProfileService


@dataclass
class NPIFactor:
    name: str
    weight: float
    score: float
    explanation: str


class NPIEngine:
    """Calculate the 200-point Nik Power Index.

    ``weight`` is the maximum contribution of a factor.  Individual
    factor scores are always clamped to that factor's weight so the
    aggregate can never exceed the published 200-point scale.
    """

    MAX_SCORE = 200

    weight_profiles = NPIWeightProfileService()

    DEFAULT_WEIGHTS = {
        "home_advantage": 20,
        "spread_value": 35,
        "market_environment": 25,
        "situational_edge": 40,
        "historical_rules": 80,
    }

    LEGACY_FACTOR_NAMES = {
        "Home Advantage": "home_advantage",
        "Spread Value": "spread_value",
        "Market Environment": "market_environment",
        "Situational Edge": "situational_edge",
        "Historical Rule Engine": "historical_rules",
    }

    def __init__(self, weights=None):
        normalized_weights = {
            self.LEGACY_FACTOR_NAMES.get(name, name): weight
            for name, weight in (weights or {}).items()
        }
        self.weights = {
            **self.DEFAULT_WEIGHTS,
            **normalized_weights,
        }

        if round(sum(self.weights.values()), 6) != self.MAX_SCORE:
            raise ValueError(
                "NPI factor weights must total 200 points"
            )

    def calculate(
        self,
        game,
        odds,
        sport="NFL",
        model_version=None,
        db=None,
    ):
        weights = self.weights
        if db is not None:
            try:
                weights = self.weight_profiles.get_profile(
                    db=db,
                    sport=sport,
                    model_version=model_version,
                )
            except ValueError as error:
                if "No NPI weight profile found for" not in str(error):
                    raise

        factors = [
            self.home_advantage(game, weights["home_advantage"]),
            self.spread_value(odds, weights["spread_value"]),
            self.market_position(odds, weights["market_environment"]),
            self.situational_edge(game, weights["situational_edge"]),
            self.rule_match(odds, weights["historical_rules"]),
        ]

        for factor in factors:
            factor.score = max(
                0,
                min(factor.score, factor.weight),
            )

        total = self._score_total(factors)

        return {
            "npi_score": total,
            "max_score": self.MAX_SCORE,
            "sport": sport,
            "model_version": model_version,
            "factors": [
                {
                    "name": factor.name,
                    "weight": factor.weight,
                    "score": factor.score,
                    "explanation": factor.explanation,
                }
                for factor in factors
            ],
        }

    def _score_total(self, factors):
        return round(
            max(
                0.0,
                min(
                    sum(factor.score for factor in factors),
                    self.MAX_SCORE,
                ),
            ),
            2,
        )

    def home_advantage(self, game, weight: float):
        return NPIFactor(
            name="Home Advantage",
            weight=weight,
            score=weight,
            explanation="Home team advantage applied",
        )

    def spread_value(self, odds, weight: float):
        spread = abs(float(odds.spread_home or 0))

        if spread <= 3:
            strength = 1.0
        elif spread <= 7:
            strength = 0.65
        else:
            strength = 0.35

        return NPIFactor(
            name="Spread Value",
            weight=weight,
            score=round(weight * strength, 2),
            explanation=f"Spread difficulty evaluated: {spread}",
        )

    def market_position(self, odds, weight: float):
        total = float(odds.total or 0)

        if total >= 50:
            strength = 1.0
            explanation = "High scoring environment"
        elif total >= 40:
            strength = 0.65
            explanation = "Normal scoring environment"
        else:
            strength = 0.40
            explanation = "Lower scoring environment"

        return NPIFactor(
            name="Market Environment",
            weight=weight,
            score=round(weight * strength, 2),
            explanation=explanation,
        )

    def situational_edge(self, game, weight: float):
        return NPIFactor(
            name="Situational Edge",
            weight=weight,
            score=round(weight * 0.50, 2),
            explanation="Situational factors evaluated",
        )

    def rule_match(self, odds, weight: float):
        spread = float(odds.spread_home or 0)
        strength = 0.0
        explanations = []

        if spread == -5.5:
            strength += 0.35
            explanations.append("-5.5 home historical rule")

        if spread == -7.5:
            strength += 0.25
            explanations.append("-7.5 historical rule")

        if spread == -4.5:
            strength += 0.25
            explanations.append("-4.5 historical rule")

        strength = min(strength, 1.0)

        return NPIFactor(
            name="Historical Rule Engine",
            weight=weight,
            score=round(weight * strength, 2),
            explanation=(
                " | ".join(explanations)
                if explanations
                else "No historical rule matched"
            ),
        )
