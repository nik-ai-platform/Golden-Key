from __future__ import annotations


class DataLicenseService:
    def grant_access(self, client: str) -> dict:
        return {
            "client": client,
            "access": ["NBA Historical Database", "NPI Scores", "Simulation Results", "Research Reports", "Analytics Feeds"],
        }
