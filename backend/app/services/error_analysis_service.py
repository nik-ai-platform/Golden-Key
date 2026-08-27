class ErrorAnalysisService:

    def classify_error(self, error_type):
        error_type = (error_type or "VARIANCE").upper()
        if error_type == "MODEL_ERROR":
            return {"classification": "MODEL_ERROR", "reason": "Feature weighting issue"}
        if error_type == "MARKET_ERROR":
            return {"classification": "MARKET_ERROR", "reason": "Market moved unexpectedly"}
        if error_type == "DATA_ERROR":
            return {"classification": "DATA_ERROR", "reason": "Missing injury/news information"}
        return {"classification": "VARIANCE", "reason": "Correct process, bad outcome"}
