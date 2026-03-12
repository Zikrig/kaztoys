from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class HiddenAuthor(Base):
    __tablename__ = "hidden_authors"
    __table_args__ = (
        UniqueConstraint("user_id", "hidden_user_id", "reason", name="uq_hidden_authors_user_hidden_reason"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    hidden_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    report_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("reports.id"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
