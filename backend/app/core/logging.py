import logging


def setup_logging():

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )


logger = logging.getLogger("nik-ai")


def _structured(event: str, **kwargs):
    fields = " ".join(f"{key}={value}" for key, value in kwargs.items())
    return f"event={event} {fields}".strip()


def log_prediction_created(game_id: int, pick: str, confidence: float):
    logger.info(_structured("Prediction Created", game_id=game_id, pick=pick, confidence=confidence))


def log_model_run(model: str, game_id: int, status: str):
    logger.info(_structured("Model Run", model=model, game_id=game_id, status=status))


def log_ai_response(game_id: int, summary: str):
    logger.info(_structured("AI Response", game_id=game_id, summary=summary))


def log_pipeline_failure(stage: str, reason: str):
    logger.error(_structured("Pipeline Failure", stage=stage, reason=reason))


def log_user_activity(user_id: int, action: str):
    logger.info(_structured("User Activity", user_id=user_id, action=action))
