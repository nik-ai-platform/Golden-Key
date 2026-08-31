from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
	pass


# Ensure metadata includes stored prediction table during migration autogeneration.
from app.models.prediction_record import Prediction  # noqa: E402,F401
from app.models.ai_analysis import AIAnalysis  # noqa: E402,F401
from app.models.pipeline_run import PipelineRun  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.recovery_email_verification import RecoveryEmailVerification  # noqa: E402,F401
from app.models.forgot_email_challenge import ForgotEmailChallenge  # noqa: E402,F401
from app.models.user_prediction import UserPrediction  # noqa: E402,F401
from app.models.subscription import Subscription  # noqa: E402,F401
from app.models.prediction_result import PredictionResult  # noqa: E402,F401
from app.models.npi_factor_result import NPIFactorResult  # noqa: E402,F401
from app.models.model_version import ModelVersion  # noqa: E402,F401
from app.models.npi_weight_profile import NPIWeightProfile  # noqa: E402,F401
from app.models.prediction_line_correction import PredictionLineCorrection  # noqa: E402,F401
