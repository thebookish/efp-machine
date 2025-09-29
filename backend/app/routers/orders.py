from fastapi import  Request
from app.services.order_ingest import enqueue_order
from app.services.parse import parse_single_message
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from app.deps import get_db
from app.models import Order
from app.schemas import OrderResponse, OrderUpdate
from app.services.fetch_messages import fetch_and_process_messages
from app.services.simple_parser import simple_parse_message

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
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return list(result.scalars().all())


def _serialize_orders(orders: list[Order]) -> list[dict]:
    return [
        OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
        for o in orders
    ]


async def _push_full_list(db: AsyncSession):
    """Broadcast the entire order list (used after bulk changes)."""
    orders = await _fetch_orders(db)
    await manager.broadcast_json(
        {"type": "orders_list", "payload": _serialize_orders(orders)}
    )


async def _push_order_update(order: Order):
    """Broadcast a single order update (used after edit)."""
    order_dict = OrderResponse.model_validate(order, from_attributes=True).model_dump(mode="json")
    await manager.broadcast_json(
        {"type": "order_update", "payload": order_dict}
    )


# --- WebSocket feed ---
@router.websocket("/ws")
async def orders_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(ws)
    try:
        await ws.send_json(
            {"type": "orders_list", "payload": _serialize_orders(await _fetch_orders(db))}
        )
        while True:
            await asyncio.sleep(60)  # keep connection alive
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
        try:
            await ws.close()
        except Exception:
            pass

# --- Slack Events ---
@router.post("/slack/events")
async def slack_events(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Slack event callbacks.
    If it's a message event, parse it and create orders just like fetch API.
    """
    payload = await request.json()
    event_type = payload.get("type")

    # Step 1: URL Verification (Slack handshake)
    if event_type == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Step 2: Event callback
    if event_type == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "message" and "subtype" not in event:
            text = event.get("text")
            user = event.get("user")
            ts = event.get("ts")
            channel = event.get("channel")

            # Build fake event+msg_obj like your fetch API
            fake_event = {"eventId": ts}
            msg_obj = {
                "message": text,
                "timestamp": ts,
                "sender": {"uuid": user},
            }

            parsed_orders = parse_single_message(fake_event, msg_obj)
            if parsed_orders:
                if not isinstance(parsed_orders, list):
                    parsed_orders = [parsed_orders]

                for order in parsed_orders:
                    await enqueue_order(order)

                await _push_full_list(db)  # broadcast updates to frontend

                return {"status": "accepted", "queued": len(parsed_orders)}

            return {"status": "ignored", "reason": "not an order message"}

    return {"status": "ok"}

# --- Fetch orders from external API ---
@router.post("/fetch")
async def fetch_orders_from_api(db: AsyncSession = Depends(get_db)):
    """
    Fetch new messages from external API, parse, and enqueue into DB.
    """
    try:
        result = await fetch_and_process_messages()
        await _push_full_list(db)  # broadcast after fetch
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed fetching messages: {e}")


# --- List orders ---
@router.get("/list", response_model=list[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return result.scalars().all()


# --- Edit order ---
@router.put("/edit/{order_id}", response_model=OrderResponse)
async def edit_order(order_id: str, updates: OrderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.orderId == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = updates.model_dump(exclude_unset=True)

    # If response is being updated, parse it and auto-update fields
    if "response" in update_data and update_data["response"]:
        parsed = simple_parse_message(update_data["response"])
        if parsed:
            order.contractId = parsed.get("contractId")
            order.expiryDate = parsed.get("expiryDate")
            order.buySell = parsed.get("buySell")
            order.price = parsed.get("price")
            order.basis = parsed.get("basis")

    # Apply other updates
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)

    # Push single update to frontend
    await _push_order_update(order)

    return order
