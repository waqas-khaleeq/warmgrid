from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SetupRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SenderMailboxCreate(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    target_daily_volume: int = 50


class SenderMailboxUpdate(BaseModel):
    display_name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    target_daily_volume: Optional[int] = None
    is_active: Optional[bool] = None


class SenderMailboxOut(BaseModel):
    id: int
    email: str
    display_name: Optional[str]
    domain: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    imap_host: str
    imap_port: int
    imap_username: str
    is_active: bool
    is_paused: bool
    current_daily_volume: int
    target_daily_volume: int
    warmup_week: int
    health_score: float
    last_health_check: Optional[datetime]
    warmup_start_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SeedMailboxCreate(BaseModel):
    email: EmailStr
    app_password: str
    provider: Optional[str] = None


class SeedMailboxOut(BaseModel):
    id: int
    email: str
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    provider: str
    is_active: bool
    last_used: Optional[datetime]
    emails_received_total: int
    replies_sent_total: int
    spam_rescues_total: int
    created_at: datetime

    class Config:
        from_attributes = True


class WarmupEmailOut(BaseModel):
    id: int
    sender_mailbox_id: int
    seed_mailbox_id: int
    message_id: Optional[str]
    subject: Optional[str]
    body_preview: Optional[str]
    sent_at: Optional[datetime]
    received_at: Optional[datetime]
    replied_at: Optional[datetime]
    found_in_spam: bool
    rescued_from_spam: bool
    reply_received: bool
    status: str

    class Config:
        from_attributes = True


class HealthLogOut(BaseModel):
    id: int
    sender_mailbox_id: int
    health_score: float
    spam_rate: float
    reply_rate: float
    bounce_rate: float
    emails_sent_today: int
    emails_received_today: int
    spam_rescued_today: int
    blacklisted: bool
    blacklist_details: Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


class ActivityLogOut(BaseModel):
    id: int
    level: str
    mailbox_id: Optional[int]
    mailbox_email: Optional[str]
    action: str
    message: str
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AppSettingsUpdate(BaseModel):
    content_mode: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    deepseek_max_retries: Optional[str] = None
    send_hour_start: Optional[str] = None
    send_hour_end: Optional[str] = None
    weekly_volume_increase: Optional[str] = None
    max_daily_volume: Optional[str] = None
    imap_poll_interval_minutes: Optional[str] = None
    health_check_interval_hours: Optional[str] = None
    min_delay_between_sends_seconds: Optional[str] = None
    max_delay_between_sends_seconds: Optional[str] = None
    min_seeds_per_send: Optional[str] = None
    max_seeds_per_send: Optional[str] = None
    auto_pause_health_threshold: Optional[str] = None


class DeepSeekTestRequest(BaseModel):
    api_key: str


class DeepSeekTestResult(BaseModel):
    success: bool
    error: Optional[str] = None
    latency_ms: int
    model: str


class ConnectionTestResult(BaseModel):
    smtp: dict
    imap: dict


class MailboxStats(BaseModel):
    emails_sent_total: int
    emails_received_total: int
    reply_rate: float
    spam_rate: float
    bounce_rate: float
    spam_rescued_total: int
    health_score: float
    current_daily_volume: int
    target_daily_volume: int
    warmup_week: int
    warmup_progress_percent: float
    daily_sends_last_30_days: list
    health_scores_last_30_days: list


class AnalyticsOverview(BaseModel):
    total_sender_mailboxes: int
    active_mailboxes: int
    paused_mailboxes: int
    total_seed_mailboxes: int
    active_seeds: int
    emails_sent_today: int
    emails_sent_this_week: int
    emails_sent_total: int
    replies_received_today: int
    overall_reply_rate: float
    spam_rescues_today: int
    spam_rescues_total: int
    average_health_score: float
    mailboxes_on_blacklist: int
    warmup_emails_in_last_7_days: list


class ContentPoolStats(BaseModel):
    mailbox_id: int
    mailbox_email: str
    total_used_combos: int
    unique_subjects_used: int
    unique_bodies_used: int
    template_pool_size: int
    pool_exhaustion_percent: float
    deepseek_generated_total: int
    template_generated_total: int
    pool_resets_total: int
    last_reset_at: Optional[datetime]
    estimated_days_until_exhaustion: int
