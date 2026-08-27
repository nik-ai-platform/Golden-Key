from __future__ import annotations


class AIGuardrailService:
    def apply_guardrails(self, response: str) -> str:
        response = response.strip()
        if response.lower().startswith("this will win"):
            return "I cannot guarantee outcomes. The model identifies this as a high-value opportunity with transparent confidence levels."
        return response + " This recommendation is educational and should be paired with risk disclosure and responsible betting practices."
