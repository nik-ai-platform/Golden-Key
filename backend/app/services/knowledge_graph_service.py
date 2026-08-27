from __future__ import annotations

from typing import Any


class KnowledgeGraphService:
    def build_graph(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        data = data or {}
        sport = str(data.get("sport", "NBA"))

        nodes = [
            {"id": "teams", "type": "Teams"},
            {"id": "players", "type": "Players"},
            {"id": "strategies", "type": "Strategies"},
            {"id": "conditions", "type": "Conditions"},
            {"id": "outcomes", "type": "Outcomes"},
            {"id": "patterns", "type": "Patterns"},
            {"id": "back_to_back", "type": "Condition"},
            {"id": "fatigue", "type": "Mechanism"},
            {"id": "lower_shooting", "type": "Performance"},
            {"id": "under_performance", "type": "Outcome"},
        ]
        edges = [
            {"from": "back_to_back", "to": "fatigue", "label": "increases"},
            {"from": "fatigue", "to": "lower_shooting", "label": "drives"},
            {"from": "lower_shooting", "to": "under_performance", "label": "causes"},
            {"from": "patterns", "to": "strategies", "label": "informs"},
        ]

        return {
            "sport": sport,
            "nodes": nodes,
            "edges": edges,
            "path_example": ["Back-to-back", "Fatigue", "Lower Shooting %", "Under Performance"],
        }
