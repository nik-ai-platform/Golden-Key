class UserLearningService:
    def track(self, user_id, question=None, concept=None, mistake=None, improvement=None):
        events = []
        if question:
            events.append({"type": "question", "value": question})
        if concept:
            events.append({"type": "concept", "value": concept})
        if mistake:
            events.append({"type": "mistake", "value": mistake})
        if improvement:
            events.append({"type": "improvement", "value": improvement})

        return {
            "user_id": user_id,
            "events": events,
            "preferences": {
                "emphasize_expected_value": any("expected value" in (item.get("value") or "").lower() for item in events),
            },
        }
