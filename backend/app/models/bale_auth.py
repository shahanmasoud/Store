from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CustomerAccount(Base):
    __tablename__ = "customer_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_customer_provider_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="bale")
    provider_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_login_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class BaleLoginChallenge(Base):
    __tablename__ = "bale_login_challenges"
    __table_args__ = (
        Index("ix_bale_login_challenges_code_hash_status", "code_hash", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    return_path: Mapped[str] = mapped_column(String(255), nullable=False, default="/")
    bale_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bale_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bale_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_accounts.id"), nullable=True, index=True
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    approved_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
