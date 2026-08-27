from __future__ import annotations

from app.core.golden_key_engine import GoldenKeyEngine


def run_prediction_worker(game_id: int) -> dict:
    return GoldenKeyEngine().analyze_game(game_id)
