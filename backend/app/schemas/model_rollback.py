from pydantic import BaseModel


class ModelRollbackRequest(BaseModel):

    sport: str
    target_version: str
    approved_by: str
    reason: str | None = None
