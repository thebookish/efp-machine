from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from app.config import settings

def to_async_url(url_str: str) -> str:
    """Force the DATABASE_URL to use async drivers."""
    u = make_url(url_str)
    if u.drivername.startswith("sqlite"):
        u = u.set(drivername="sqlite+aiosqlite")
    elif u.drivername.startswith("postgresql"):
        u = u.set(drivername="postgresql+asyncpg")
    return str(u)

async_url = to_async_url(settings.DATABASE_URL)

# Configure engine with better pooling
engine = create_async_engine(
    async_url,
    echo=False,
    future=True,
    pool_size=20,        # default is 5
    max_overflow=40,     # allow 40 extra connections on demand
    pool_timeout=30,     # seconds to wait before giving up
    pool_recycle=1800,   # recycle every 30 mins
)

# Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Utility for background jobs (outside of FastAPI request context)
async def create_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
