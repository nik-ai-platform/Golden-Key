class StrategyMarketplaceService:
    def build_catalog(self) -> list[dict]:
        return [
            {"name": "Premium Signal Pack", "tier": "premium"},
            {"name": "Research Reports", "tier": "subscription"},
            {"name": "Private Groups", "tier": "community"},
        ]
