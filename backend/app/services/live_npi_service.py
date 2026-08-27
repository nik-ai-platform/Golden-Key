class LiveNPIService:
    def calculate_live_npi(self, starting_npi, momentum, efficiency_change, player_availability, game_state):
        starting = float(starting_npi or 0)
        momentum_value = float(momentum or 0)
        efficiency = float(efficiency_change or 0)
        availability = float(player_availability or 0)
        game = float(game_state or 0)
        return round(starting + momentum_value + efficiency + availability + game, 2)
