from app.services.fetch_messages import fetch_and_process_messages
from app.services.parse import parse_single_message
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from datetime import datetime, timezone
from fastapi import  Request
from app.deps import get_db
from app.models import BloombergMessage, Order
from app.schemas import BloombergMessageResponse, OrderResponse, OrderUpdate
from .bloomberg_msg import message_manager  # reuse WS manager

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

# --- List orders ---
@router.get("/list", response_model=list[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return result.scalars().all()

@router.post("/slack/events")
async def slack_events(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Slack event callbacks.
    If it's a message event, check if it's trade-related via parse_single_message.
    If yes, store it in BloombergMessage table (status = drafted).
    """
    payload = await request.json()
    event_type = payload.get("type")

    # --- Step 1: URL Verification (Slack handshake)
    if event_type == "url_verification":
        return {"challenge": payload.get("challenge")}

    # --- Step 2: Event callback
    if event_type == "event_callback":
        event = payload.get("event", {})
        if event.get("type") == "message" and "subtype" not in event:
            text = event.get("text")
            user = event.get("user")
            ts = event.get("ts")

            # Build fake event+msg_obj for parser
            fake_event = {"eventId": payload.get("event_id")}
            msg_obj = {
                "message": text,
                "timestamp": ts,
                "sender": {"uuid": user},
            }

            # parse
            parsed_meta = parse_single_message(fake_event, msg_obj)

            if parsed_meta:
                # Save in BloombergMessage table
                new_msg = BloombergMessage(
                    eventId=parsed_meta["eventId"],
                    roomId=event.get("channel"),
                    originalMessage=text,
                    trader_uuid=parsed_meta.get("trader_uuid"),
                    trader_legalEntityShortName=None,  # can enrich later from Users table
                    trader_alias=None,
                    original_llm_json=None,
                    current_json=None,
                    is_edited=False,
                    messageStatus="drafted",
                )
                db.add(new_msg)
                await db.commit()
                await db.refresh(new_msg)

                # Broadcast to WS clients
                payload = BloombergMessageResponse.model_validate(
                    new_msg, from_attributes=True
                ).model_dump(mode="json")
                await message_manager.broadcast_json(
                    {"type": "message_new", "payload": payload}
                )

                return {"status": "stored", "eventId": parsed_meta["eventId"]}

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
