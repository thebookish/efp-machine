from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.deps import get_db
from app.models import BlotterTrade
from app.schemas import BlotterTradeBase, BlotterTradeResponse, BlotterRemoveRequest
from typing import List

router = APIRouter(prefix="/api/blotter", tags=["blotter"])


@router.post("/add", response_model=BlotterTradeResponse)
async def add_trade(req: BlotterTradeBase, db: AsyncSession = Depends(get_db)):
    # Normalize
    side = req.side.upper()
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")

    res = await db.execute(
        select(BlotterTrade).where(
            BlotterTrade.index_name == req.index_name,
            BlotterTrade.side == side,
        )
    )
    trade = res.scalar_one_or_none()

    if trade:
        # Update existing trade → recalc avg price
        total_qty = trade.qty + req.qty
        trade.avg_price = (trade.avg_price * trade.qty + req.price * req.qty) / total_qty
        trade.qty = total_qty
    else:
        trade = BlotterTrade(
            side=side,
            index_name=req.index_name,
            qty=req.qty,
            avg_price=req.price,
        )
        db.add(trade)

    await db.commit()
    await db.refresh(trade)
    return trade


@router.post("/remove")
async def remove_trade(req: BlotterRemoveRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BlotterTrade).where(BlotterTrade.id == req.trade_id))
    trade = res.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    await db.execute(delete(BlotterTrade).where(BlotterTrade.id == req.trade_id))
    await db.commit()
    return {"detail": f"Trade {req.trade_id} removed"}


@router.get("/list", response_model=List[BlotterTradeResponse])
async def list_trades(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BlotterTrade).order_by(BlotterTrade.created_at.desc()))
    return res.scalars().all()
