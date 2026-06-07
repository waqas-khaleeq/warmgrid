import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import ActivityLog
from schemas import ActivityLogOut

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[ActivityLogOut])
async def get_logs(
    mailbox_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = []
    if mailbox_id:
        filters.append(ActivityLog.mailbox_id == mailbox_id)
    if level and level != "all":
        filters.append(ActivityLog.level == level)
    if start_date:
        try:
            filters.append(ActivityLog.created_at >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            filters.append(ActivityLog.created_at <= datetime.fromisoformat(end_date))
        except ValueError:
            pass
    if search:
        filters.append(ActivityLog.message.ilike(f"%{search}%"))

    query = select(ActivityLog)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(ActivityLog.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/export")
async def export_logs(
    mailbox_id: Optional[int] = Query(None),
    level: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = []
    if mailbox_id:
        filters.append(ActivityLog.mailbox_id == mailbox_id)
    if level and level != "all":
        filters.append(ActivityLog.level == level)
    if start_date:
        try:
            filters.append(ActivityLog.created_at >= datetime.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            filters.append(ActivityLog.created_at <= datetime.fromisoformat(end_date))
        except ValueError:
            pass

    query = select(ActivityLog)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(ActivityLog.created_at.desc()).limit(10000)
    result = await db.execute(query)
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "created_at", "level", "mailbox_id", "mailbox_email", "action", "message", "details"])
    for log in logs:
        writer.writerow([log.id, log.created_at, log.level, log.mailbox_id, log.mailbox_email, log.action, log.message, log.details])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=warmgrid_logs.csv"},
    )
