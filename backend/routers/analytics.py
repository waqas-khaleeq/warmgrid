from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import SenderMailbox, SeedMailbox, WarmupEmail, HealthLog

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    total_senders = (await db.execute(select(func.count(SenderMailbox.id)))).scalar() or 0
    active_senders = (await db.execute(select(func.count(SenderMailbox.id)).where(SenderMailbox.is_active == True, SenderMailbox.is_paused == False))).scalar() or 0
    paused_senders = (await db.execute(select(func.count(SenderMailbox.id)).where(SenderMailbox.is_paused == True))).scalar() or 0
    total_seeds = (await db.execute(select(func.count(SeedMailbox.id)))).scalar() or 0
    active_seeds = (await db.execute(select(func.count(SeedMailbox.id)).where(SeedMailbox.is_active == True))).scalar() or 0

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    sent_today = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.sent_at >= today_start))).scalar() or 0
    sent_week = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.sent_at >= week_start))).scalar() or 0
    sent_total = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.status != "failed"))).scalar() or 0

    replies_today = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.replied_at >= today_start))).scalar() or 0
    replies_total = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.reply_received == True))).scalar() or 0
    overall_reply_rate = round((replies_total / sent_total * 100) if sent_total > 0 else 0.0, 1)

    rescued_today = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.rescued_from_spam == True, WarmupEmail.sent_at >= today_start))).scalar() or 0
    rescued_total = (await db.execute(select(func.count(WarmupEmail.id)).where(WarmupEmail.rescued_from_spam == True))).scalar() or 0

    avg_health = (await db.execute(select(func.avg(SenderMailbox.health_score)).where(SenderMailbox.is_active == True))).scalar() or 100.0

    bl_result = await db.execute(
        select(func.count(func.distinct(HealthLog.sender_mailbox_id))).where(
            HealthLog.blacklisted == True,
            HealthLog.recorded_at >= today_start - timedelta(days=1),
        )
    )
    mailboxes_on_bl = bl_result.scalar() or 0

    # Last 7 days per day
    seven_days = []
    for i in range(6, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = (await db.execute(
            select(func.count(WarmupEmail.id)).where(
                WarmupEmail.sent_at >= day_start,
                WarmupEmail.sent_at < day_end,
            )
        )).scalar() or 0
        seven_days.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    return {
        "total_sender_mailboxes": total_senders,
        "active_mailboxes": active_senders,
        "paused_mailboxes": paused_senders,
        "total_seed_mailboxes": total_seeds,
        "active_seeds": active_seeds,
        "emails_sent_today": sent_today,
        "emails_sent_this_week": sent_week,
        "emails_sent_total": sent_total,
        "replies_received_today": replies_today,
        "overall_reply_rate": overall_reply_rate,
        "spam_rescues_today": rescued_today,
        "spam_rescues_total": rescued_total,
        "average_health_score": round(avg_health, 1),
        "mailboxes_on_blacklist": mailboxes_on_bl,
        "warmup_emails_in_last_7_days": seven_days,
    }


@router.get("/mailbox/{mailbox_id}")
async def get_mailbox_analytics(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Mailbox not found")

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    daily_result = await db.execute(
        select(
            func.date(WarmupEmail.sent_at).label("date"),
            func.count(WarmupEmail.id).label("count"),
        ).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.sent_at >= thirty_days_ago,
        ).group_by(func.date(WarmupEmail.sent_at))
    )
    daily_sends = [{"date": str(r.date), "count": r.count} for r in daily_result.all()]

    health_result = await db.execute(
        select(HealthLog).where(
            HealthLog.sender_mailbox_id == mailbox_id,
            HealthLog.recorded_at >= thirty_days_ago,
        ).order_by(HealthLog.recorded_at.asc())
    )
    health_history = [
        {"date": str(r.recorded_at.date()), "score": r.health_score, "spam_rate": r.spam_rate, "reply_rate": r.reply_rate}
        for r in health_result.scalars().all()
    ]

    return {
        "mailbox_id": mailbox_id,
        "email": mailbox.email,
        "daily_sends_30d": daily_sends,
        "health_history_30d": health_history,
    }


@router.get("/content-stats")
async def get_content_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from models import UsedContent
    from content_engine import get_exhaustion_stats, SUBJECT_TEMPLATES, BODY_TEMPLATES

    result = await db.execute(select(SenderMailbox).where(SenderMailbox.is_active == True))
    mailboxes = result.scalars().all()

    stats = []
    for mailbox in mailboxes:
        exhaustion = await get_exhaustion_stats(db, mailbox.id)

        ds_count = (await db.execute(
            select(func.count(UsedContent.id)).where(
                UsedContent.sender_mailbox_id == mailbox.id,
                UsedContent.content_source == "deepseek",
            )
        )).scalar() or 0

        tmpl_count = (await db.execute(
            select(func.count(UsedContent.id)).where(
                UsedContent.sender_mailbox_id == mailbox.id,
                UsedContent.content_source == "templates",
            )
        )).scalar() or 0

        last_reset_result = await db.execute(
            select(func.min(UsedContent.used_at)).where(UsedContent.sender_mailbox_id == mailbox.id)
        )
        last_reset = last_reset_result.scalar()

        stats.append({
            "mailbox_id": mailbox.id,
            "mailbox_email": mailbox.email,
            "total_used": exhaustion["total_used"],
            "unique_subjects_used": exhaustion["unique_subjects_used"],
            "unique_bodies_used": exhaustion["unique_bodies_used"],
            "template_pool_size": exhaustion["template_pool_size"],
            "pool_exhaustion_percent": exhaustion["pool_exhaustion_percent"],
            "deepseek_generated_total": ds_count,
            "template_generated_total": tmpl_count,
            "pool_resets_total": 0,
            "last_reset_at": last_reset,
            "estimated_days_until_exhaustion": exhaustion["estimated_days_until_reset"],
        })

    return stats
