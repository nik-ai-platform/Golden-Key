from __future__ import annotations


class AgentMessageService:
    def __init__(self) -> None:
        self._messages: list[dict] = []

    def send(self, sender: str, receiver: str, message: str) -> dict:
        payload = {"sender": sender, "receiver": receiver, "message": message}
        self._messages.append(payload)
        return payload

    def history(self) -> list[dict]:
        return list(self._messages)
