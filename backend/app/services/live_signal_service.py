class LiveSignalService:
    def generate_signal(self, signal_type, details):
        signal_type = (signal_type or "WATCH").upper()
        return {
            "signal": signal_type,
            "details": details or {},
            "message": f"{signal_type} signal generated",
        }
