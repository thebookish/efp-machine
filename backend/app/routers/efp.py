from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.deps import get_db
from app.schemas import UpdatePriceRequest, TradeRequest, CommandResult
from app.models import EfpRun, Recap
from app.services.efp_protocol import is_worsening, require_cash_ref_on_update, format_recap
import asyncio

router = APIRouter(prefix='/api/efp', tags=['efp'])

EFP_CLIENTS = set()
RECAP_CLIENTS = set()

async def broadcast_efp(session: AsyncSession):
    rows = await session.execute(select(EfpRun).order_by(EfpRun.index_name))
    payload = [{
        'index_name': r.index_name,
        'bid': r.bid,
        'offer': r.offer,
        'cash_ref': r.cash_ref
    } for r in rows.scalars()]
    for ws in list(EFP_CLIENTS):
        try:
            await ws.send_json(payload)
        except Exception:
            EFP_CLIENTS.discard(ws)

async def broadcast_recaps(session: AsyncSession):
    rows = await session.execute(select(Recap).order_by(Recap.created_at.desc()).limit(50))
    payload = [{
        'index_name': r.index_name,
        'price': r.price,
        'lots': r.lots,
        'cash_ref': r.cash_ref,
        'recap_text': r.recap_text,
    } for r in rows.scalars()]
    for ws in list(RECAP_CLIENTS):
        try:
            await ws.send_json(payload)
        except Exception:
            RECAP_CLIENTS.discard(ws)

@router.websocket('/ws/run')
async def ws_run(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    EFP_CLIENTS.add(ws)
    try:
        while True:
            await broadcast_efp(db)
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        EFP_CLIENTS.discard(ws)

@router.websocket('/ws/recaps')
async def ws_recaps(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    RECAP_CLIENTS.add(ws)
    try:
        while True:
            await broadcast_recaps(db)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        RECAP_CLIENTS.discard(ws)

@router.get('/run')
async def get_run(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EfpRun).order_by(EfpRun.index_name))
    rows = result.scalars().all()
    return [{ 'index_name': r.index_name, 'bid': r.bid, 'offer': r.offer, 'cash_ref': r.cash_ref } for r in rows]

@router.post('/update', response_model=CommandResult)
async def update_price(req: UpdatePriceRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EfpRun).where(EfpRun.index_name == req.index))
    row = res.scalar_one_or_none()
    if row is None:
        row = EfpRun(index_name=req.index, bid=req.bid, offer=req.offer, cash_ref=req.cash_ref)
        db.add(row)
        await db.commit()
        await broadcast_efp(db)
        return CommandResult(ok=True, detail='Created new row', requires_cash_ref=(req.cash_ref is None))
    requires_confirmation = False
    if req.bid is not None and is_worsening(row.bid, req.bid, 'bid') and not req.dean_confirm:
        requires_confirmation = True
    if req.offer is not None and is_worsening(row.offer, req.offer, 'offer') and not req.dean_confirm:
        requires_confirmation = True
    if requires_confirmation:
        return CommandResult(ok=False, detail='Worsening detected; Dean confirmation required.', requires_confirmation=True)
    if req.bid is not None:
        row.bid = req.bid
    if req.offer is not None:
        row.offer = req.offer
    if req.cash_ref is not None:
        row.cash_ref = req.cash_ref
    await db.commit()
    await broadcast_efp(db)
    return CommandResult(ok=True, detail='Updated', requires_cash_ref=require_cash_ref_on_update(row.cash_ref, req.cash_ref))

@router.post('/trade', response_model=CommandResult)
async def trade(req: TradeRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EfpRun).where(EfpRun.index_name == req.index))
    row = res.scalar_one_or_none()
    if row:
        await db.execute(delete(EfpRun).where(EfpRun.index_name == req.index))
    cash_ref = req.cash_ref if req.cash_ref is not None else (row.cash_ref if row else None)
    recap_text = format_recap(req.index, req.price, req.lots, cash_ref)
    db.add(Recap(index_name=req.index, price=req.price, lots=req.lots, cash_ref=cash_ref, recap_text=recap_text))
    await db.commit()
    await broadcast_efp(db)
    await broadcast_recaps(db)
    prompt = f'Ask for price on the follow — {req.index}'
    return CommandResult(ok=True, detail=prompt, recap=recap_text)
