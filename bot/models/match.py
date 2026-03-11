from datetime import datetime
from sqlalchemy import Boolean, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("listings.id"), nullable=False, index=True)
    response_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("responses.id"), nullable=False, unique=True, index=True)
    listing_owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    response_owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    listing_owner_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    response_owner_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing = relationship("Listing", back_populates="matches", foreign_keys=[listing_id])
    response = relationship("Response", back_populates="match", foreign_keys=[response_id])
