from pydantic import BaseModel
from typing import Any


class APIResponse(BaseModel):

    success: bool

    message: str

    data: Any = None
