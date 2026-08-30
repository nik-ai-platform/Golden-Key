class MomentumService:

    def calculate_momentum(self, scoring_run, time_remaining, efficiency_change=None, possession=None, turnovers=None, shot_quality=None, pace_change=None):
        if scoring_run is None:
            return 0

        scoring_run_value = float(scoring_run)
        time_value = float(time_remaining or 0)
        efficiency = float(efficiency_change or 0)
        possession_value = float(possession or 0)
        turnover_penalty = float(turnovers or 0)
        shot_quality_value = float(shot_quality or 0)
        pace = float(pace_change or 0)
        momentum = round(scoring_run_value * 1.5 + efficiency + possession_value - turnover_penalty + shot_quality_value + pace - (time_value / 10), 2)
        if scoring_run_value > 10 and time_value <= 60:
            corroborating_signals = (
                efficiency,
                possession_value,
                turnover_penalty,
                shot_quality_value,
                pace,
            )
            bonus = 6 if any(corroborating_signals) else 1
            momentum = round(momentum + bonus, 2)
        return momentum
