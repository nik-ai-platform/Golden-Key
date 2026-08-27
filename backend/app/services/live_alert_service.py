class LiveAlertService:
    def create_alert(self, alert_type, payload):
        return {
            "alert": alert_type,
            "payload": payload or {},
            "message": "Alert triggered",
        }
