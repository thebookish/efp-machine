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
async_url = settings.DATABASE_URL

engine = create_async_engine(async_url, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
# add this near the bottom of deps.py
async def create_session() -> AsyncSession:
    """Utility for background jobs (non-request context)."""
    async with AsyncSessionLocal() as session:
        yield session
