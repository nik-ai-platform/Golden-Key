from pydantic import BaseModel


class TeamBase(BaseModel):
    name: str
    league: str
    sport: str
    power_rating: float = 0


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: int

    class Config:
        from_attributes = True
