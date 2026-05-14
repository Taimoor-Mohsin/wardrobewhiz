from app.core.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outfit_name = Column(String, nullable=False)
    outfit_description = Column(Text, nullable=True)
    styling_tips = Column(Text, nullable=True)
    color_story = Column(Text, nullable=True)
    why_it_fits_you = Column(Text, nullable=True)
    item_ids = Column(Text, nullable=True)
    context_occasion = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
