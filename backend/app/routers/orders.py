# import uuid
# import json
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from app.deps import get_db
# from app.models import Order
# from app.schemas import OrderResponse
# from app.services.parse import parse_bbg_message

# router = APIRouter(prefix="/api/orders", tags=["orders"])

# @router.post("/load")
# async def load_bbg_data(db: AsyncSession = Depends(get_db)):
#     try:
#         with open("bbg_data.json", "r") as f:
#             events = json.load(f)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to load JSON: {e}")

#     inserted = 0
#     for ev in events:
#         parsed = parse_bbg_message(ev)
#         if not parsed:
#             continue

#         # Skip if already exists
#         exists = await db.execute(
#             select(Order).where(Order.client_provided_id == parsed.client_provided_id)
#         )
#         if exists.scalar_one_or_none():
#             continue

#         order = Order(
#             id=str(uuid.uuid4()),
#             client_provided_id=parsed.client_provided_id,
#             symbol=parsed.symbol,
#             side=parsed.side,
#             basis=parsed.basis,
#             price=parsed.price,
#         )
#         db.add(order)
#         inserted += 1

#     await db.commit()
#     return {"inserted": inserted, "status": "ok"}

# @router.get("/list", response_model=list[OrderResponse])
# async def list_orders(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Order).order_by(Order.created_at.desc()))
#     return result.scalars().all()
# app/routers/orders.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid, json, asyncio

from app.deps import get_db
from app.models import Order
from app.schemas import OrderResponse, OrderUpdate
from app.services.parse import parse_bbg_message

router = APIRouter(prefix="/api/orders", tags=["orders"])

# --- WebSocket manager ---
class OrdersWSManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self.active.discard(ws)

    async def broadcast_json(self, message: dict):
        dead = []
        async with self._lock:
            for ws in list(self.active):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active.discard(ws)

manager = OrdersWSManager()

# --- Helpers ---
async def _fetch_orders(db: AsyncSession) -> list[Order]:
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return list(result.scalars().all())

def _serialize_orders(orders: list[Order]) -> list[dict]:
    return [
        OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
        for o in orders
    ]

async def _push_full_list(db: AsyncSession):
    orders = await _fetch_orders(db)
    await manager.broadcast_json({
        "type": "orders_list",
        "payload": _serialize_orders(orders),
    })

# --- WebSocket: live updates ---
@router.websocket("/ws")
async def orders_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(ws)
    try:
        # Send the latest list immediately
        await ws.send_json({
            "type": "orders_list",
            "payload": _serialize_orders(await _fetch_orders(db)),
        })

        # Then just keep it alive until the client disconnects
        while True:
            await asyncio.sleep(3600)  # long sleep, keeps loop alive
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    finally:
        await manager.disconnect(ws)


# --- Upload BBG JSON file ---
@router.post("/upload")
async def upload_bbg_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed")

    try:
        contents = await file.read()
        events = json.loads(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {e}")

    if not isinstance(events, list):
        events = [events]

    inserted = 0
    for ev in events:
        parsed = parse_bbg_message(ev)
        if not parsed:
            continue

        order = Order(
            id=str(uuid.uuid4()),
            message=parsed.message,
            orderType=parsed.orderType,
            buySell=parsed.buySell,
            quantity=parsed.quantity,
            price=parsed.price,
            basis=parsed.basis,
            strategyDisplayName=parsed.strategyDisplayName,
            contractId=parsed.contractId,
            expiryDate=parsed.expiryDate,
        )
        db.add(order)
        inserted += 1

    await db.commit()
    await _push_full_list(db)

    return {"inserted": inserted, "status": "ok"}

# --- Fallback GET list ---
@router.get("/list", response_model=list[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_db)):
    return await _fetch_orders(db)

# --- Edit order ---
@router.put("/edit/{order_id}", response_model=OrderResponse)
async def edit_order(order_id: str, updates: OrderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)
    await _push_full_list(db)

    return order
