from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.sql import func


class OutfitFeedback(Base):
    __tablename__ = "outfit_feedback"

    id = Column(Integer, primary_key=True, index=True)
    outfit_id = Column(Integer, ForeignKey("outfits.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # +1 (like) or -1 (dislike)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
