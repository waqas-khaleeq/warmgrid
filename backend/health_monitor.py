import json
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


async def calculate_health_score(
    db: AsyncSession,
    sender_mailbox,
    spam_rate: float,
    reply_rate: float,
    bounce_rate: float,
    blacklisted: bool,
) -> float:
    score = 100.0
    if spam_rate > 10:
        score -= 35
    if reply_rate < 20:
        score -= 25
    if bounce_rate > 5:
        score -= 20
    if blacklisted:
        score -= 10

    # Volume ramp consistency check
    if sender_mailbox.warmup_week > 2:
        expected_volume = min(
            sender_mailbox.target_daily_volume,
            5 + (sender_mailbox.warmup_week - 1) * 5
        )
        if sender_mailbox.current_daily_volume < expected_volume * 0.7:
            score -= 10

    return max(0.0, min(100.0, score))


async def save_health_log(
    db: AsyncSession,
    sender_mailbox_id: int,
    health_score: float,
    spam_rate: float,
    reply_rate: float,
    bounce_rate: float,
    emails_sent_today: int,
    emails_received_today: int,
    spam_rescued_today: int,
    blacklisted: bool,
    blacklist_details: str = None,
):
    from models import HealthLog, SenderMailbox
    log = HealthLog(
        sender_mailbox_id=sender_mailbox_id,
        health_score=health_score,
        spam_rate=spam_rate,
        reply_rate=reply_rate,
        bounce_rate=bounce_rate,
        emails_sent_today=emails_sent_today,
        emails_received_today=emails_received_today,
        spam_rescued_today=spam_rescued_today,
        blacklisted=blacklisted,
        blacklist_details=blacklist_details,
        recorded_at=datetime.utcnow(),
    )
    db.add(log)

    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == sender_mailbox_id))
    mailbox = result.scalar_one_or_none()
    if mailbox:
        mailbox.health_score = health_score
        mailbox.last_health_check = datetime.utcnow()
    await db.flush()
