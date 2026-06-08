import os
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Support both SQLite (local dev) and PostgreSQL (production on Render + Neon)
_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./warmgrid.db")

# Neon/Render provide postgres:// or postgresql:// — convert to asyncpg driver
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    _raw_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# asyncpg doesn't accept psycopg2-style query params (sslmode, channel_binding, etc.)
# Strip all query params from the URL — SSL is handled via connect_args below.
if not _raw_url.startswith("sqlite"):
    parsed = urlparse(_raw_url)
    _raw_url = urlunparse(parsed._replace(query=""))

DATABASE_URL = _raw_url
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# SQLite needs check_same_thread=False
# PostgreSQL with Neon needs SSL
if IS_SQLITE:
    _connect_args = {"check_same_thread": False}
    _engine_kwargs = {}
else:
    # Neon requires SSL — asyncpg uses ssl="require" in connect_args
    _connect_args = {"ssl": "require"}
    # Connection pooling settings for free Neon tier (max 10 connections)
    _engine_kwargs = {
        "pool_size": 5,
        "max_overflow": 2,
        "pool_recycle": 300,   # recycle connections every 5 min
        "pool_pre_ping": True, # test connection before using from pool
    }

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables():
    from models import (  # noqa: F401
        User, SenderMailbox, SeedMailbox, WarmupEmail,
        HealthLog, ActivityLog, AppSettings, UsedContent
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
