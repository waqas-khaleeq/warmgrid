import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from database import create_all_tables, AsyncSessionLocal
from routers import auth, mailboxes, seeds, logs, analytics, settings as settings_router

DEFAULT_SETTINGS = {
    "content_mode": "templates",
    "deepseek_api_key": "",
    "deepseek_max_retries": "3",
    "send_hour_start": "7",
    "send_hour_end": "11",
    "weekly_volume_increase": "5",
    "max_daily_volume": "50",
    "imap_poll_interval_minutes": "120",
    "health_check_interval_hours": "24",
    "min_delay_between_sends_seconds": "60",
    "max_delay_between_sends_seconds": "300",
    "min_seeds_per_send": "5",
    "max_seeds_per_send": "8",
    "auto_pause_health_threshold": "50",
}


async def seed_default_settings():
    from models import AppSettings
    async with AsyncSessionLocal() as db:
        for key, value in DEFAULT_SETTINGS.items():
            result = await db.execute(select(AppSettings).where(AppSettings.setting_key == key))
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(AppSettings(setting_key=key, setting_value=value, updated_at=datetime.utcnow()))
        await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_all_tables()
    await seed_default_settings()

    from scheduler import scheduler, setup_scheduler

    try:
        async with AsyncSessionLocal() as db:
            from models import AppSettings

            async def get_s(k, d):
                r = await db.execute(select(AppSettings).where(AppSettings.setting_key == k))
                row = r.scalar_one_or_none()
                return int(row.setting_value) if row else int(d)

            send_start = await get_s("send_hour_start", 7)
            send_end = await get_s("send_hour_end", 11)
            imap_interval = await get_s("imap_poll_interval_minutes", 120)
            health_interval = await get_s("health_check_interval_hours", 24)
    except Exception:
        send_start, send_end, imap_interval, health_interval = 7, 11, 120, 24

    setup_scheduler(send_start, send_end, imap_interval, health_interval)
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


# Build allowed origins list
_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]
_frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _frontend_url:
    _origins.append(_frontend_url)

app = FastAPI(title="WarmGrid API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(mailboxes.router)
app.include_router(seeds.router)
app.include_router(logs.router)
app.include_router(analytics.router)
app.include_router(settings_router.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
