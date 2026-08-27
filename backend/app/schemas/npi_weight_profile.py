from pydantic import BaseModel, Field


class NPIWeightCreate(BaseModel):

    sport: str
    model_version: str
    factor_name: str
    weight: float = Field(ge=0, le=200)


class NPIWeightUpdate(BaseModel):

    weight: float = Field(ge=0, le=200)


class NPIWeightResponse(BaseModel):

    id: int
    sport: str
    model_version: str
    factor_name: str
    weight: float
    is_active: bool

    class Config:
        from_attributes = True
