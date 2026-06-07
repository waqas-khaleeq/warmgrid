import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import SenderMailbox, WarmupEmail, HealthLog, ActivityLog
from schemas import SenderMailboxCreate, SenderMailboxUpdate, SenderMailboxOut
from smtp_sender import test_smtp_connection
from imap_listener import test_imap_connection

router = APIRouter(prefix="/api/mailboxes", tags=["mailboxes"])


def _extract_domain(email: str) -> str:
    return email.split("@")[-1].lower()


class SmtpTestRequest(BaseModel):
    host: str
    port: int
    username: str
    password: str


class ImapTestRequest(BaseModel):
    host: str
    port: int
    username: str
    password: str


@router.get("", response_model=list[SenderMailboxOut])
async def list_mailboxes(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).order_by(SenderMailbox.created_at.desc()))
    return result.scalars().all()


@router.post("/test-smtp")
async def test_smtp_endpoint(body: SmtpTestRequest, _=Depends(get_current_user)):
    return await test_smtp_connection(body.host, body.port, body.username, body.password)


@router.post("/test-imap")
async def test_imap_endpoint(body: ImapTestRequest, _=Depends(get_current_user)):
    return await test_imap_connection(body.host, body.port, body.username, body.password)


@router.post("")
async def create_mailbox(body: SenderMailboxCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings

    smtp_result, imap_result = await asyncio.gather(
        test_smtp_connection(body.smtp_host, body.smtp_port, body.smtp_username, body.smtp_password),
        test_imap_connection(body.imap_host, body.imap_port, body.imap_username, body.imap_password),
    )

    if not smtp_result["success"]:
        raise HTTPException(status_code=400, detail=f"SMTP connection failed: {smtp_result['error']}")
    if not imap_result["success"]:
        raise HTTPException(status_code=400, detail=f"IMAP connection failed: {imap_result['error']}")

    existing = await db.execute(select(SenderMailbox).where(SenderMailbox.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A mailbox with this email already exists")

    mailbox = SenderMailbox(
        email=body.email,
        display_name=body.display_name,
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_username=body.smtp_username,
        smtp_password=settings.encrypt(body.smtp_password),
        imap_host=body.imap_host,
        imap_port=body.imap_port,
        imap_username=body.imap_username,
        imap_password=settings.encrypt(body.imap_password),
        domain=_extract_domain(body.email),
        target_daily_volume=body.target_daily_volume,
        current_daily_volume=5,
        warmup_start_date=datetime.utcnow(),
        health_score=100.0,
    )
    db.add(mailbox)
    await db.flush()
    return {
        "mailbox": SenderMailboxOut.model_validate(mailbox).model_dump(),
        "smtp_test": smtp_result,
        "imap_test": imap_result,
    }


@router.get("/{mailbox_id}", response_model=SenderMailboxOut)
async def get_mailbox(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return mailbox


@router.put("/{mailbox_id}", response_model=SenderMailboxOut)
async def update_mailbox(mailbox_id: int, body: SenderMailboxUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    if body.smtp_host is not None:
        mailbox.smtp_host = body.smtp_host
    if body.smtp_port is not None:
        mailbox.smtp_port = body.smtp_port
    if body.smtp_username is not None:
        mailbox.smtp_username = body.smtp_username
    if body.smtp_password is not None:
        mailbox.smtp_password = settings.encrypt(body.smtp_password)
    if body.imap_host is not None:
        mailbox.imap_host = body.imap_host
    if body.imap_port is not None:
        mailbox.imap_port = body.imap_port
    if body.imap_username is not None:
        mailbox.imap_username = body.imap_username
    if body.imap_password is not None:
        mailbox.imap_password = settings.encrypt(body.imap_password)
    if body.display_name is not None:
        mailbox.display_name = body.display_name
    if body.target_daily_volume is not None:
        mailbox.target_daily_volume = body.target_daily_volume
    if body.is_active is not None:
        mailbox.is_active = body.is_active
    mailbox.updated_at = datetime.utcnow()
    await db.flush()
    return mailbox


@router.delete("/{mailbox_id}")
async def delete_mailbox(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    await db.delete(mailbox)
    await db.flush()
    return {"deleted": True}


@router.post("/{mailbox_id}/pause")
async def toggle_pause(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    mailbox.is_paused = not mailbox.is_paused
    await db.flush()
    return {"is_paused": mailbox.is_paused}


@router.post("/{mailbox_id}/test")
async def test_mailbox_connection(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    smtp_pass = settings.decrypt(mailbox.smtp_password)
    imap_pass = settings.decrypt(mailbox.imap_password)

    smtp_result, imap_result = await asyncio.gather(
        test_smtp_connection(mailbox.smtp_host, mailbox.smtp_port, mailbox.smtp_username, smtp_pass),
        test_imap_connection(mailbox.imap_host, mailbox.imap_port, mailbox.imap_username, imap_pass),
    )
    return {"smtp": smtp_result, "imap": imap_result}


@router.get("/{mailbox_id}/stats")
async def get_mailbox_stats(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    total_sent_r = await db.execute(
        select(func.count(WarmupEmail.id)).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.status != "failed",
        )
    )
    total_sent = total_sent_r.scalar() or 0

    total_received_r = await db.execute(
        select(func.count(WarmupEmail.id)).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.received_at.isnot(None),
        )
    )
    total_received = total_received_r.scalar() or 0

    total_replied_r = await db.execute(
        select(func.count(WarmupEmail.id)).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.reply_received == True,
        )
    )
    total_replied = total_replied_r.scalar() or 0

    total_spam_r = await db.execute(
        select(func.count(WarmupEmail.id)).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.found_in_spam == True,
        )
    )
    total_spam = total_spam_r.scalar() or 0

    total_rescued_r = await db.execute(
        select(func.count(WarmupEmail.id)).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.rescued_from_spam == True,
        )
    )
    total_rescued = total_rescued_r.scalar() or 0

    reply_rate = round((total_replied / total_sent * 100) if total_sent > 0 else 0.0, 1)
    spam_rate = round((total_spam / total_sent * 100) if total_sent > 0 else 0.0, 1)
    warmup_progress = round(
        (mailbox.current_daily_volume / mailbox.target_daily_volume * 100)
        if mailbox.target_daily_volume > 0 else 0.0, 1
    )

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_sends_r = await db.execute(
        select(
            func.date(WarmupEmail.sent_at).label("date"),
            func.count(WarmupEmail.id).label("count"),
        ).where(
            WarmupEmail.sender_mailbox_id == mailbox_id,
            WarmupEmail.sent_at >= thirty_days_ago,
        ).group_by(func.date(WarmupEmail.sent_at))
    )
    daily_sends = [{"date": str(r.date), "count": r.count} for r in daily_sends_r.all()]

    health_r = await db.execute(
        select(HealthLog).where(
            HealthLog.sender_mailbox_id == mailbox_id,
            HealthLog.recorded_at >= thirty_days_ago,
        ).order_by(HealthLog.recorded_at.asc())
    )
    health_scores = [
        {"date": str(r.recorded_at.date()), "score": r.health_score}
        for r in health_r.scalars().all()
    ]

    return {
        "emails_sent_total": total_sent,
        "emails_received_total": total_received,
        "reply_rate": reply_rate,
        "spam_rate": spam_rate,
        "bounce_rate": 0.0,
        "spam_rescued_total": total_rescued,
        "health_score": mailbox.health_score,
        "current_daily_volume": mailbox.current_daily_volume,
        "target_daily_volume": mailbox.target_daily_volume,
        "warmup_week": mailbox.warmup_week,
        "warmup_progress_percent": warmup_progress,
        "daily_sends_last_30_days": daily_sends,
        "health_scores_last_30_days": health_scores,
    }
