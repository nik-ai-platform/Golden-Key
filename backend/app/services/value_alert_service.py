class ValueAlertService:
    def check(self, model_projection, best_market, edge_threshold=1.5):
        if model_projection is None or best_market is None:
            return None

        projected = float(model_projection)
        market = float(best_market)
        edge = round(projected - market, 2)
        if edge >= edge_threshold:
            return {
                "alert": "🔥 VALUE ALERT",
                "edge": edge,
                "message": f"Model projection {projected} vs best market {market} creates {edge} points of edge",
            }
        return None
