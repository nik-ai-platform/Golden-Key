class AlertService:

    def create_alert(self, alert_type, details):
        if not alert_type:
            return None

        return {
            "alert_type": alert_type,
            "message": details.get("message", "Alert generated"),
            "value": details.get("value", "LOW"),
            "confidence": details.get("confidence", 0),
        }
