from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class SearchFilters(Base):
    __tablename__ = "search_filters"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), primary_key=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="search_filters")
