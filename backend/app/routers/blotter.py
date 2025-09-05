from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime
import asyncio

from app.deps import get_db
from app.models import BlotterTrade
from app.schemas import (
    BlotterTradeBase,
    BlotterTradeResponse,
    BlotterRemoveRequest,
)

router = APIRouter(prefix="/api/blotter", tags=["blotter"])

BLOTTER_CLIENTS = set()


# ----------------- WebSocket for live blotter -----------------
async def broadcast_blotter(session: AsyncSession):
    res = await session.execute(
        select(BlotterTrade).order_by(BlotterTrade.created_at.desc())
    )
    trades = res.scalars().all()
    payload = [
        {
            "id": t.id,
            "side": t.side,
            "index_name": t.index_name,
            "qty": t.qty,
            "avg_price": t.avg_price,
            "created_at": t.created_at.isoformat(),
        }
        for t in trades
    ]

    for ws in list(BLOTTER_CLIENTS):
        try:
            await ws.send_json(payload)
        except Exception:
            BLOTTER_CLIENTS.discard(ws)


@router.websocket("/ws/list")
async def ws_blotter(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    BLOTTER_CLIENTS.add(ws)
    try:
        while True:
            await broadcast_blotter(db)
            await asyncio.sleep(2)  # refresh every 2 sec
    except WebSocketDisconnect:
        BLOTTER_CLIENTS.discard(ws)


# ----------------- REST endpoints -----------------
@router.post("/add", response_model=BlotterTradeResponse)
async def add_trade(req: BlotterTradeBase, db: AsyncSession = Depends(get_db)):
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
        total_qty = trade.qty + req.qty
        trade.avg_price = round(
            (trade.avg_price * trade.qty + req.price * req.qty) / total_qty, 4
        )
        trade.qty = total_qty
    else:
        trade = BlotterTrade(
            side=side,
            index_name=req.index_name.upper(),
            qty=req.qty,
            avg_price=req.price,
            created_at=datetime.utcnow(),
        )
        db.add(trade)

    await db.commit()
    await db.refresh(trade)
    # notify WS clients
    await broadcast_blotter(db)
    return BlotterTradeResponse.from_orm(trade)


@router.post("/remove")
async def remove_trade(req: BlotterRemoveRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(BlotterTrade).where(BlotterTrade.id == req.trade_id))
    trade = res.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    await db.execute(delete(BlotterTrade).where(BlotterTrade.id == req.trade_id))
    await db.commit()
    await broadcast_blotter(db)
    return {"detail": f"Trade {req.trade_id} removed"}


@router.get("/list", response_model=List[BlotterTradeResponse])
async def list_trades(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(BlotterTrade).order_by(BlotterTrade.created_at.desc())
    )
    trades = res.scalars().all()
    return [BlotterTradeResponse.from_orm(t) for t in trades]
