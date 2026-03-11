from datetime import datetime
from sqlalchemy import Boolean, BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("listings.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    chosen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing = relationship("Listing", back_populates="responses", foreign_keys=[listing_id])
    user = relationship("User", back_populates="responses", foreign_keys=[user_id])
    match = relationship("Match", back_populates="response", uselist=False, foreign_keys="Match.response_id")
