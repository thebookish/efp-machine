from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import get_db
from app.models import Instrument
from app.schemas import InstrumentResponse

router = APIRouter(prefix="/api/instruments", tags=["instruments"])


# --- List all instruments ---
@router.get("/", response_model=list[InstrumentResponse])
async def list_instruments(db: AsyncSession = Depends(get_db)):
    """
    Return all instruments.
    """
    result = await db.execute(select(Instrument))
    instruments = result.scalars().all()
    return instruments


# --- Get instrument by tradeable_id ---
@router.get("/{tradeable_id}", response_model=InstrumentResponse)
async def get_instrument(tradeable_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a single instrument by its tradeable_id.
    """
    result = await db.execute(select(Instrument).where(Instrument.tradeable_id == tradeable_id))
    instrument = result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return instrument
