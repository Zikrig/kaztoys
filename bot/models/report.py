from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reporter_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("listings.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    admin_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    reporter = relationship("User", back_populates="filed_reports", foreign_keys=[reporter_user_id])
    target_user = relationship("User", back_populates="received_reports", foreign_keys=[target_user_id])
    listing = relationship("Listing", back_populates="reports", foreign_keys=[listing_id])
