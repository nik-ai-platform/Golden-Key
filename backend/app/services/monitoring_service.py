import logging


class MonitoringService:
    """
    Centralized application logging with a consistent format.
    """


    def __init__(
        self,
        logger=None,
    ):
        self.logger = logger or logging.getLogger(__name__)


    def _format_context(
        self,
        context: dict
    ) -> str:

        if not context:
            return ""

        parts = []

        for key, value in context.items():
            parts.append(f"{key}={value}")

        return " ".join(parts)


    def log_prediction(
        self,
        message: str,
        **context
    ):

        details = self._format_context(context)

        if details:
            self.logger.info(
                f"[PREDICTION] {message} {details}"
            )
            return

        self.logger.info(
            f"[PREDICTION] {message}"
        )


    def log_import(
        self,
        message: str,
        **context
    ):

        details = self._format_context(context)

        if details:
            self.logger.info(
                f"[IMPORT] {message} {details}"
            )
            return

        self.logger.info(
            f"[IMPORT] {message}"
        )


    def log_scheduler(
        self,
        message: str,
        **context
    ):

        details = self._format_context(context)

        if details:
            self.logger.info(
                f"[SCHEDULER] {message} {details}"
            )
            return

        self.logger.info(
            f"[SCHEDULER] {message}"
        )


    def log_exception(
        self,
        message: str,
        **context
    ):

        details = self._format_context(context)

        if details:
            self.logger.error(
                f"[ERROR] {message} {details}"
            )
            return

        self.logger.error(
            f"[ERROR] {message}"
        )


    def log_error(
        self,
        message: str,
        **context
    ):
        return self.log_exception(
            message,
            **context
        )
