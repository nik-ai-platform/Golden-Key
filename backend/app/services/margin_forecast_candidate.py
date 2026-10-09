from __future__ import annotations

import math
from numbers import Real


MODEL_VERSION = "MARKET-MARGIN-CANDIDATE-1.0"
ACTIVATION_ENABLED = False


def forecast_home_margin_from_spread(spread_home: Real) -> float:
    """Return the market-implied home score margin from the frozen home line."""
    if isinstance(spread_home, bool) or not isinstance(spread_home, Real):
        raise ValueError("spread_home must be a finite numeric line")

    line = float(spread_home)
    if not math.isfinite(line):
        raise ValueError("spread_home must be a finite numeric line")

    return -line
