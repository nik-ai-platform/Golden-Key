class LiveStreamService:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)
        return True

    def publish(self, payload):
        for subscriber in self.subscribers:
            subscriber(payload)
        return {"delivered": len(self.subscribers)}

    def reconnect(self):
        return {"status": "reconnected"}
