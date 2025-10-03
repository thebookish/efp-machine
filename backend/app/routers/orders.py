from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from datetime import datetime, timezone

from app.deps import get_db
from app.models import Order
from app.schemas import OrderResponse, OrderUpdate

router = APIRouter(prefix="/api/orders", tags=["orders"])


# --- WebSocket manager for orders ---
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
            if ws in self.active:
                self.active.remove(ws)

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
async def _fetch_orders(db: AsyncSession):
    result = await db.execute(select(Order).order_by(Order.createdAt.desc()))
    return list(result.scalars().all())


def _serialize_orders(orders: list[Order]) -> list[dict]:
    return [
        OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
        for o in orders
    ]


async def _push_full_list(db: AsyncSession):
    orders = await _fetch_orders(db)
    await manager.broadcast_json(
        {"type": "orders_list", "payload": _serialize_orders(orders)}
    )


async def _push_order_update(order: Order):
    order_dict = OrderResponse.model_validate(order, from_attributes=True).model_dump(mode="json")
    await manager.broadcast_json({"type": "order_update", "payload": order_dict})


# --- WebSocket feed ---
@router.websocket("/ws")
async def orders_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(ws)
    try:
        await ws.send_json(
            {"type": "orders_list", "payload": _serialize_orders(await _fetch_orders(db))}
        )
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
        try:
            await ws.close()
        except Exception:
            pass


# --- Update order status ---
@router.post("/update-order/{order_id}", response_model=OrderResponse)
async def update_order(order_id: str, updates: OrderUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update an order's status (orderStatus).
    Append the change into orderStatusHistory with timestamp.
    """
    result = await db.execute(select(Order).where(Order.orderId == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = updates.model_dump(exclude_unset=True)

    # Handle orderStatus updates with history tracking
    if "state" in update_data or "orderStatus" in update_data:
        new_status = update_data.get("state") or update_data.get("orderStatus")
        if new_status and new_status != order.orderStatus:
            order.orderStatus = new_status
            history = order.orderStatusHistory or []
            history.append({
                "orderStatus": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            order.orderStatusHistory = history

    # Apply other updates
    for field, value in update_data.items():
        if hasattr(order, field) and field not in ["state", "orderStatusHistory"]:
            setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    # Broadcast update
    await _push_order_update(order)

    return order
