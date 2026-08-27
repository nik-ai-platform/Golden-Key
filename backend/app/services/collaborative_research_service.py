from __future__ import annotations


class CollaborativeResearchService:
    def __init__(self) -> None:
        self._experiments: list[dict] = []
        self._notes: list[dict] = []
        self._comments: list[dict] = []
        self._versions: list[dict] = []
        self._approvals: list[dict] = []

    def shared_experiment(self, payload: dict) -> dict:
        experiment = {"name": payload.get("name", "Untitled Experiment"), "status": "shared", "id": len(self._experiments) + 1}
        self._experiments.append(experiment)
        return experiment

    def add_note(self, payload: dict) -> dict:
        note = {"author": payload.get("author", "analyst01"), "text": payload.get("text", ""), "id": len(self._notes) + 1}
        self._notes.append(note)
        return note

    def add_comment(self, payload: dict) -> dict:
        comment = {"author": payload.get("author", "researcher01"), "text": payload.get("text", ""), "id": len(self._comments) + 1}
        self._comments.append(comment)
        return comment

    def record_version(self, payload: dict) -> dict:
        version = {"label": payload.get("label", "v1"), "id": len(self._versions) + 1}
        self._versions.append(version)
        return version

    def approve(self, payload: dict) -> dict:
        approval = {"approved": payload.get("approved", True), "id": len(self._approvals) + 1}
        self._approvals.append(approval)
        return approval
