from __future__ import annotations

from typing import Any


class AdaptiveNPIService:
    def calculate_personal_npi(self, base_npi: dict[str, Any], user_profile: dict[str, Any]) -> dict[str, Any]:
        preference = (user_profile.get("preferred_bet_types") or ["ATS"])[0]
        adjustment = 0
        if preference == "ATS":
            adjustment = 12
        elif preference == "MONEYLINE":
            adjustment = 4

        return {
            "base_npi": base_npi,
            "personal_adjustment": adjustment,
            "personal_npi_view": {
                "home_advantage": base_npi.get("home_advantage", 10) + adjustment,
                "preference": preference,
            },
        }
