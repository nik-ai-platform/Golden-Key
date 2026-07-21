from sqlalchemy import Column, Integer, String, Float

from app.database.base import Base


class Injury(Base):

    __tablename__ = "injuries"


    id = Column(
        Integer,
        primary_key=True
    )


    team = Column(
        String
    )


    player = Column(
        String
    )


    status = Column(
        String
    )


    impact = Column(
        Float
    )
