# app/deps.py
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy.engine import URL
from app.config import settings

def to_async_url(url_str: str) -> str:
    """Force DATABASE_URL to use async drivers."""
    u = make_url(url_str)
    if u.drivername.startswith("sqlite"):
        u = u.set(drivername="sqlite+aiosqlite")
    elif u.drivername.startswith("postgresql"):
        u = u.set(drivername="postgresql+asyncpg")
    return str(u)
url = URL.create(
    "postgresql+asyncpg",
    username="neondb_owner",
    password="npg_kaERqV3XBD6s",
    host="ep-frosty-voice-ad7jm1zk-pooler.c-2.us-east-1.aws.neon.tech",
    port=5432,
    database="efp1",
)
ssl_ctx = ssl.create_default_context()
# async_url = to_async_url(settings.DATABASE_URL)

# Bigger pool for bursts

engine = create_async_engine(
    url,
    # async_url,
    connect_args={"ssl": ssl_ctx},
    pool_size=50,          # Number of persistent connections
    max_overflow=150,       # Temporary burst connections
    pool_timeout=30,       # Seconds to wait for a connection
    pool_recycle=1800,     # Recycle connections every 30 mins
    pool_pre_ping=True,    # Detect & refresh stale connections
    echo=False,
    future=True,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
