from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, JSON

from app.database.base import Base


class UserBehavior(Base):
    __tablename__ = "user_behavior"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    games_viewed = Column(Integer, nullable=True, default=0)
    predictions_viewed = Column(Integer, nullable=True, default=0)
    bets_accepted = Column(Integer, nullable=True, default=0)
    bets_ignored = Column(Integer, nullable=True, default=0)
    favorite_teams = Column(JSON, nullable=True)
    average_odds = Column(String, nullable=True)
    win_loss_patterns = Column(JSON, nullable=True)
    bankroll_changes = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)
