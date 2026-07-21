from sqlalchemy.orm import Session

from app.schemas.team import TeamCreate
from app.repositories import team_repository


def create_team(
    db: Session,
    team: TeamCreate
):

    return team_repository.create_team(
        db,
        team
    )


def get_teams(
    db: Session
):

    return team_repository.get_teams(db)
