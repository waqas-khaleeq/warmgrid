from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer, String, Boolean, DateTime, Float, Text, ForeignKey,
    UniqueConstraint, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SenderMailbox(Base):
    __tablename__ = "sender_mailboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    smtp_username: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_password: Mapped[str] = mapped_column(Text, nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    imap_username: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_password: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    current_daily_volume: Mapped[int] = mapped_column(Integer, default=5)
    target_daily_volume: Mapped[int] = mapped_column(Integer, default=50)
    warmup_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    warmup_week: Mapped[int] = mapped_column(Integer, default=1)
    health_score: Mapped[float] = mapped_column(Float, default=100.0)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    warmup_emails: Mapped[list["WarmupEmail"]] = relationship("WarmupEmail", back_populates="sender_mailbox", cascade="all, delete-orphan")
    health_logs: Mapped[list["HealthLog"]] = relationship("HealthLog", back_populates="sender_mailbox", cascade="all, delete-orphan")
    used_contents: Mapped[list["UsedContent"]] = relationship("UsedContent", back_populates="sender_mailbox", cascade="all, delete-orphan")


class SeedMailbox(Base):
    __tablename__ = "seed_mailboxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    imap_host: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_username: Mapped[str] = mapped_column(String(255), nullable=False)
    app_password: Mapped[str] = mapped_column(Text, nullable=False)
    smtp_host: Mapped[str] = mapped_column(String(255), nullable=False)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    provider: Mapped[str] = mapped_column(String(50), default="other")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime)
    emails_received_total: Mapped[int] = mapped_column(Integer, default=0)
    replies_sent_total: Mapped[int] = mapped_column(Integer, default=0)
    spam_rescues_total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    warmup_emails: Mapped[list["WarmupEmail"]] = relationship("WarmupEmail", back_populates="seed_mailbox")
    used_contents: Mapped[list["UsedContent"]] = relationship("UsedContent", back_populates="seed_mailbox")


class WarmupEmail(Base):
    __tablename__ = "warmup_emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_mailbox_id: Mapped[int] = mapped_column(Integer, ForeignKey("sender_mailboxes.id"), nullable=False)
    seed_mailbox_id: Mapped[int] = mapped_column(Integer, ForeignKey("seed_mailboxes.id"), nullable=False)
    message_id: Mapped[Optional[str]] = mapped_column(String(512))
    subject: Mapped[Optional[str]] = mapped_column(String(512))
    body_preview: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    found_in_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    rescued_from_spam: Mapped[bool] = mapped_column(Boolean, default=False)
    reply_received: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="sent")

    sender_mailbox: Mapped["SenderMailbox"] = relationship("SenderMailbox", back_populates="warmup_emails")
    seed_mailbox: Mapped["SeedMailbox"] = relationship("SeedMailbox", back_populates="warmup_emails")


class HealthLog(Base):
    __tablename__ = "health_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_mailbox_id: Mapped[int] = mapped_column(Integer, ForeignKey("sender_mailboxes.id"), nullable=False)
    health_score: Mapped[float] = mapped_column(Float, default=100.0)
    spam_rate: Mapped[float] = mapped_column(Float, default=0.0)
    reply_rate: Mapped[float] = mapped_column(Float, default=0.0)
    bounce_rate: Mapped[float] = mapped_column(Float, default=0.0)
    emails_sent_today: Mapped[int] = mapped_column(Integer, default=0)
    emails_received_today: Mapped[int] = mapped_column(Integer, default=0)
    spam_rescued_today: Mapped[int] = mapped_column(Integer, default=0)
    blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_details: Mapped[Optional[str]] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sender_mailbox: Mapped["SenderMailbox"] = relationship("SenderMailbox", back_populates="health_logs")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(20), default="info")
    mailbox_id: Mapped[Optional[int]] = mapped_column(Integer)
    mailbox_email: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    setting_value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsedContent(Base):
    __tablename__ = "used_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_mailbox_id: Mapped[int] = mapped_column(Integer, ForeignKey("sender_mailboxes.id"), nullable=False)
    seed_mailbox_id: Mapped[int] = mapped_column(Integer, ForeignKey("seed_mailboxes.id"), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_preview: Mapped[str] = mapped_column(String(60), nullable=False)
    body_preview: Mapped[str] = mapped_column(String(100), nullable=False)
    content_source: Mapped[str] = mapped_column(String(20), default="templates")
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sender_mailbox: Mapped["SenderMailbox"] = relationship("SenderMailbox", back_populates="used_contents")
    seed_mailbox: Mapped["SeedMailbox"] = relationship("SeedMailbox", back_populates="used_contents")

    __table_args__ = (
        UniqueConstraint("sender_mailbox_id", "seed_mailbox_id", "content_hash", name="uq_sender_seed_content"),
        Index("ix_used_content_sender", "sender_mailbox_id"),
    )
