class TrustService:
    def evaluate(self, profile: dict) -> dict:
        flags = []
        if profile.get("fake_records"):
            flags.append("fake_records")
        if profile.get("cherry_picking"):
            flags.append("cherry_picking")
        if profile.get("deleted_losses"):
            flags.append("deleted_losses")
        if profile.get("suspicious_activity"):
            flags.append("suspicious_activity")
        if profile.get("duplicate_accounts"):
            flags.append("duplicate_accounts")

        trust_score = max(0, 100 - (len(flags) * 20))
        return {"trust_score": trust_score, "flags": flags, "status": "trusted" if trust_score >= 80 else "review"}
