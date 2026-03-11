from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed_deals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onboarding_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_from_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    listings = relationship("Listing", back_populates="user", foreign_keys="Listing.user_id")
    responses = relationship("Response", back_populates="user", foreign_keys="Response.user_id")
    subscriptions = relationship("Subscription", back_populates="user")
    search_filters = relationship("SearchFilters", back_populates="user", uselist=False, lazy="selectin")
