from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.base import Base


class NikScore(Base):
    __tablename__ = "nik_scores"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(String, nullable=True)

    game = relationship("Game", back_populates="nik_scores")
