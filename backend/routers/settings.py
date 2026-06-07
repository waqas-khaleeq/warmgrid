import json
import time
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import AppSettings, UsedContent, SenderMailbox, ActivityLog
from schemas import AppSettingsUpdate, DeepSeekTestRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])

PROTECTED_KEYS = {"deepseek_api_key"}


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(AppSettings))
    rows = result.scalars().all()
    out = {}
    for row in rows:
        if row.setting_key == "deepseek_api_key":
            out[row.setting_key] = "***SET***" if row.setting_value else ""
        else:
            out[row.setting_key] = row.setting_value
    return out


@router.put("")
async def update_settings(body: AppSettingsUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings as app_settings

    updates = body.model_dump(exclude_none=True)

    for key, value in updates.items():
        if key == "deepseek_api_key":
            encrypted = app_settings.encrypt(value) if value else ""
            await _upsert_setting(db, key, encrypted)
        else:
            await _upsert_setting(db, key, str(value))

    await db.flush()

    # Reschedule jobs if timing settings changed
    timing_keys = {"send_hour_start", "send_hour_end", "imap_poll_interval_minutes", "health_check_interval_hours"}
    if any(k in updates for k in timing_keys):
        try:
            from scheduler import setup_scheduler, scheduler
            send_start = int(await _get_setting(db, "send_hour_start", "7"))
            send_end = int(await _get_setting(db, "send_hour_end", "11"))
            imap_interval = int(await _get_setting(db, "imap_poll_interval_minutes", "120"))
            health_interval = int(await _get_setting(db, "health_check_interval_hours", "24"))
            if scheduler.running:
                setup_scheduler(send_start, send_end, imap_interval, health_interval)
        except Exception:
            pass

    return {"success": True}


@router.post("/test-deepseek")
async def test_deepseek(body: DeepSeekTestRequest, _=Depends(get_current_user)):
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {body.api_key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}],
                },
            )
            latency_ms = int((time.time() - start) * 1000)
            if response.status_code == 200:
                return {"success": True, "error": None, "latency_ms": latency_ms, "model": "deepseek-chat"}
            elif response.status_code == 401:
                return {"success": False, "error": "Invalid API key", "latency_ms": latency_ms, "model": "deepseek-chat"}
            else:
                return {"success": False, "error": f"API returned {response.status_code}", "latency_ms": latency_ms, "model": "deepseek-chat"}
    except httpx.TimeoutException:
        return {"success": False, "error": "API request timed out", "latency_ms": 15000, "model": "deepseek-chat"}
    except Exception as e:
        return {"success": False, "error": f"Connection error: {str(e)}", "latency_ms": 0, "model": "deepseek-chat"}


# Content pool routes
@router.get("/content-pool")
async def get_content_pool(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from content_engine import get_exhaustion_stats

    result = await db.execute(select(SenderMailbox).where(SenderMailbox.is_active == True))
    mailboxes = result.scalars().all()
    stats = []
    for mailbox in mailboxes:
        exhaustion = await get_exhaustion_stats(db, mailbox.id)
        stats.append({"mailbox_id": mailbox.id, "mailbox_email": mailbox.email, **exhaustion})
    return stats


@router.delete("/content-pool/{mailbox_id}")
async def reset_content_pool(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from content_engine import reset_used_content

    result = await db.execute(select(SenderMailbox).where(SenderMailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    deleted = await reset_used_content(db, mailbox_id)
    await db.flush()

    log = ActivityLog(
        level="info",
        mailbox_id=mailbox_id,
        mailbox_email=mailbox.email,
        action="manual_pool_reset",
        message=f"Content pool manually reset. Deleted {deleted} records.",
        created_at=datetime.utcnow(),
    )
    db.add(log)
    await db.flush()

    return {"deleted_count": deleted, "reset_at": datetime.utcnow()}


@router.get("/content-pool/{mailbox_id}/history")
async def get_content_pool_history(mailbox_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(
        select(UsedContent, SenderMailbox.email.label("seed_email"))
        .join(SenderMailbox, SenderMailbox.id == UsedContent.sender_mailbox_id)
        .where(UsedContent.sender_mailbox_id == mailbox_id)
        .order_by(UsedContent.used_at.desc())
        .limit(50)
    )
    rows = result.all()
    return [
        {
            "subject_preview": r.UsedContent.subject_preview,
            "body_preview": r.UsedContent.body_preview,
            "content_source": r.UsedContent.content_source,
            "seed_email": r.seed_email,
            "used_at": r.UsedContent.used_at,
        }
        for r in rows
    ]


async def _upsert_setting(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(AppSettings).where(AppSettings.setting_key == key))
    row = result.scalar_one_or_none()
    if row:
        row.setting_value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(AppSettings(setting_key=key, setting_value=value))
    await db.flush()


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(AppSettings).where(AppSettings.setting_key == key))
    row = result.scalar_one_or_none()
    return row.setting_value if row else default
