# backend/app/routers/efp.py
from app.services.scheduler import get_last_prediction, publish_prediction
from app.services.efp_run import fetch_daily_efp_run
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import date
import asyncio
from app.deps import get_db
from app.schemas import (
    UpdatePriceRequest,
    TradeRequest,
    CommandResult,
    ConfirmRequest,
    PublishRequest,
)
from app.models import EfpRun, Recap
from app.services.efp_protocol import (
    is_worsening,
    require_cash_ref_on_update,
    format_recap,
    classify_expiry_status,
    deviation_watchpoint,
)

router = APIRouter(prefix="/api/efp", tags=["efp"])

EFP_CLIENTS = set()
RECAP_CLIENTS = set()


# ------------- Broadcasting -------------
async def broadcast_efp(session: AsyncSession):
    rows = await session.execute(select(EfpRun))
    payload = []
    for r in rows.scalars():
        payload.append(
            {
                "index_name": r.index_name,
                "bid": r.bid,
                "offer": r.offer,
                "cash_ref": r.cash_ref,
                "watchpoint": deviation_watchpoint(r),
                "expiry": classify_expiry_status(r.index_name, date.today()),
            }
        )

    # ✅ Force SX7E last
    payload.sort(key=lambda r: (r["index_name"] == "SX7E", r["index_name"]))

    # ✅ Also attach recaps inline
    recaps = await session.execute(
        select(Recap).order_by(Recap.created_at.desc()).limit(20)
    )
    recap_rows = [
        {
            "index_name": rr.index_name,
            "price": rr.price,
            "lots": rr.lots,
            "cash_ref": rr.cash_ref,
            "recap_text": rr.recap_text,
            "created_at": rr.created_at.isoformat(),
        }
        for rr in recaps.scalars()
    ]

    block = {"run": payload, "recaps": recap_rows}

    for ws in list(EFP_CLIENTS):
        try:
            await ws.send_json(block)
        except Exception:
            EFP_CLIENTS.discard(ws)


async def broadcast_recaps(session: AsyncSession):
    rows = await session.execute(
        select(Recap).order_by(Recap.created_at.desc()).limit(50)
    )
    payload = [
        {
            "index_name": r.index_name,
            "price": r.price,
            "lots": r.lots,
            "cash_ref": r.cash_ref,
            "recap_text": r.recap_text,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows.scalars()
    ]
    for ws in list(RECAP_CLIENTS):
        try:
            await ws.send_json(payload)
        except Exception:
            RECAP_CLIENTS.discard(ws)


# ------------- WebSockets -------------
@router.websocket("/ws/run")
async def ws_run(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    EFP_CLIENTS.add(ws)
    try:
        while True:
            await broadcast_efp(db)
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        EFP_CLIENTS.discard(ws)


@router.websocket("/ws/recaps")
async def ws_recaps(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    RECAP_CLIENTS.add(ws)
    try:
        while True:
            await broadcast_recaps(db)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        RECAP_CLIENTS.discard(ws)


# ------------- Endpoints -------------

@router.get("/run")
async def get_run(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EfpRun).order_by(EfpRun.index_name))
    rows = result.scalars().all()
    return [
        {
            "index_name": r.index_name,
            "bid": r.bid,
            "offer": r.offer,
            "cash_ref": r.cash_ref,
            "watchpoint": deviation_watchpoint(r),
        }
        for r in rows
    ]


@router.post("/update", response_model=CommandResult)
async def update_price(req: UpdatePriceRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EfpRun).where(EfpRun.index_name == req.index))
    row = res.scalar_one_or_none()

    if row is None:
        row = EfpRun(
            index_name=req.index, bid=req.bid, offer=req.offer, cash_ref=req.cash_ref
        )
        db.add(row)
        await db.commit()
        await broadcast_efp(db)
        return CommandResult(
            ok=True, detail="Created new row", requires_cash_ref=(req.cash_ref is None)
        )

    requires_confirmation = False
    if (
        req.bid is not None
        and is_worsening(row.bid, req.bid, "bid")
        and not req.dean_confirm
    ):
        requires_confirmation = True
    if (
        req.offer is not None
        and is_worsening(row.offer, req.offer, "offer")
        and not req.dean_confirm
    ):
        requires_confirmation = True

    if requires_confirmation:
        return CommandResult(
            ok=False,
            detail="Worsening detected; Dean confirmation required.",
            requires_confirmation=True,
        )

    if req.bid is not None:
        row.bid = req.bid
    if req.offer is not None:
        row.offer = req.offer
    if req.cash_ref is not None:
        row.cash_ref = req.cash_ref

    await db.commit()
    await broadcast_efp(db)

    return CommandResult(
        ok=True,
        detail="Updated",
        requires_cash_ref=require_cash_ref_on_update(row.cash_ref, req.cash_ref),
    )


@router.post("/trade", response_model=CommandResult)
async def trade(req: TradeRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EfpRun).where(EfpRun.index_name == req.index))
    row = res.scalar_one_or_none()
    if row:
        await db.execute(delete(EfpRun).where(EfpRun.index_name == req.index))

    cash_ref = req.cash_ref if req.cash_ref is not None else (row.cash_ref if row else None)
    if cash_ref is None:
        raise HTTPException(status_code=400, detail="Cash reference required")

    recap_text = format_recap(req.index, req.price, req.lots, cash_ref)
    db.add(
        Recap(
            index_name=req.index,
            price=req.price,
            lots=req.lots,
            cash_ref=cash_ref,
            recap_text=recap_text,
        )
    )
    await db.commit()

    await broadcast_efp(db)
    await broadcast_recaps(db)

    prompt = f"Ask for price on the follow — {req.index}"
    return CommandResult(ok=True, detail=prompt, recap=recap_text)


@router.post("/confirm", response_model=CommandResult)
async def confirm(req: ConfirmRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(EfpRun).where(EfpRun.index_name == req.index))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Index not found")

    # mark confirmation
    row.last_confirm_note = req.note or "Confirmed by Dean"
    await db.commit()
    await broadcast_efp(db)

    return CommandResult(ok=True, detail="Worsening confirmed")


@router.post("/publish", response_model=CommandResult)
async def publish_run(req: PublishRequest, db: AsyncSession = Depends(get_db)):
    # just snapshot the run
    result = await db.execute(select(EfpRun).order_by(EfpRun.index_name))
    rows = result.scalars().all()
    snapshot = [f"{r.index_name} {r.bid}/{r.offer} {r.cash_ref}" for r in rows]
    run_text = "EFP’s\n" + "\n".join(snapshot)
    return CommandResult(ok=True, detail="Run published", recap=run_text)


@router.get("/expiry/{index}")
async def expiry_status(index: str):
    return classify_expiry_status(index.upper(), date.today())


@router.get("/prediction")
async def get_prediction():
    return get_last_prediction() or {"detail": "No prediction yet"}


@router.post("/prediction/run-now")
async def run_prediction_now():
    await publish_prediction()
    return {"detail": "Prediction run executed manually"}


@router.get("/daily-run")
async def get_daily_run():
    rows = await fetch_daily_efp_run()
    return rows
