from __future__ import annotations


class WhiteLabelService:
    def build_branding(self, client_name: str) -> dict:
        return {
            "powered_by": "Golden Key",
            "client_branding": client_name,
            "custom_domains": [f"{client_name.lower().replace(' ', '')}.example.com"],
            "custom_dashboards": True,
            "custom_reports": True,
        }
