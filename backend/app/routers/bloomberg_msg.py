from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import asyncio

from app.deps import get_db
from app.models import BloombergMessage, Order
from app.schemas import BloombergMessageCreate, BloombergMessageResponse, BloombergMessageUpdate, OrderCreate
from app.services.parse import parse_single_message
from app.services.order_ingest import enqueue_order


# --- WebSocket Manager ---
class MessagesWSManager:
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


message_manager = MessagesWSManager()
router = APIRouter(prefix="/api/messages", tags=["bloomberg_messages"])


# --- WebSocket feed ---
@router.websocket("/ws")
async def messages_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await message_manager.connect(ws)
    try:
        result = await db.execute(select(BloombergMessage).order_by(BloombergMessage.created_at.desc()))
        msgs = result.scalars().all()
        payload = [
            BloombergMessageResponse.model_validate(m, from_attributes=True).model_dump(mode="json")
            for m in msgs
        ]
        await ws.send_json({"type": "messages_list", "payload": payload})

        while True:
            await asyncio.sleep(60)

    except WebSocketDisconnect:
        await message_manager.disconnect(ws)
    except Exception:
        await message_manager.disconnect(ws)
        try:
            await ws.close()
        except Exception:
            pass

@router.post("/", response_model=BloombergMessageResponse)
async def create_message(msg_in: BloombergMessageCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new BloombergMessage with status 'received'
    """
    new_msg = BloombergMessage(
        eventId=msg_in.eventId,
        roomId=msg_in.roomId,
        originalMessage=msg_in.originalMessage,
        trader_uuid=msg_in.trader_uuid,
        trader_legalEntityShortName=msg_in.trader_legalEntityShortName,
        trader_alias=msg_in.trader_alias,
        original_llm_json=msg_in.original_llm_json,
        current_json=msg_in.current_json,
        is_edited=msg_in.is_edited or False,
        isTarget=msg_in.isTarget or False,
        source= msg_in.source,
        messageStatus="drafted"
       
       
    )
    db.add(new_msg)
    await db.commit()
    await db.refresh(new_msg)

    # broadcast to WS clients
    payload = BloombergMessageResponse.model_validate(new_msg, from_attributes=True).model_dump(mode="json")
    await message_manager.broadcast_json({"type": "message_new", "payload": payload})

    return new_msg

# --- Accept (approve) message with optional edit ---
@router.post("/accept-message/{event_id}", response_model=BloombergMessageResponse)
async def accept_message(event_id: str, updates: BloombergMessageUpdate, db: AsyncSession = Depends(get_db)):
    """
    Accept a BloombergMessage:
      - Optionally update current_json and is_edited
      - Mark status as approved
      - Auto-create Orders (parsed from originalMessage or edited JSON)
      - Broadcast the updated message via WebSocket
    """
    result = await db.execute(select(BloombergMessage).where(BloombergMessage.eventId == event_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    status_before = msg.messageStatus

    # --- Apply edits before approval ---
    update_data = updates.model_dump(exclude_unset=True)
    if "current_json" in update_data:
        msg.current_json = update_data["current_json"]
        msg.is_edited = True
    if "is_edited" in update_data:
        msg.is_edited = update_data["is_edited"]

    msg.messageStatus = "approved"
    await db.commit()
    await db.refresh(msg)

    # --- Parse + enqueue orders only when first approved ---
    if status_before != "approved":
        parsed_orders = []

        if msg.current_json:  
            try:
                parsed_orders = []
                contractId = msg.current_json.get("contract")
                strategy = msg.current_json.get("strategy")
                basis = float(msg.current_json.get("basis", 0))

                for o in msg.current_json.get("other", []):
                    order = OrderCreate(
                        eventId=msg.eventId,
                        linkedOrderID=msg.eventId,
                        message=msg.originalMessage,
                        expiryDate=o["expiryDate"],
                        strategyID=strategy,
                        contractId=contractId,
                        side=o["side"].upper(),
                        price=float(o["price"]),
                        basis=basis,
                        traderUuid=msg.trader_uuid,
                        traderAlias=msg.trader_alias,
                        traderLegalEntityShortName=msg.trader_legalEntityShortName,
                        isTarget=msg.isTarget,
                    )
                    parsed_orders.append(order)

                print(f"✅ Parsed {len(parsed_orders)} orders from edited JSON for {msg.eventId}")

                for order in parsed_orders:
                    await enqueue_order(order)

            except Exception as e:
                print(f"⚠️ Failed parsing edited JSON for {msg.eventId}: {e}")


    # --- Broadcast updated message ---
    payload = BloombergMessageResponse.model_validate(msg, from_attributes=True).model_dump(mode="json")
    await message_manager.broadcast_json({"type": "message_update", "payload": payload})

    return msg


# --- Delete message (reject) ---
@router.post("/delete-message/{event_id}", response_model=BloombergMessageResponse)
async def delete_message(event_id: str, db: AsyncSession = Depends(get_db)):
    """
    Reject a BloombergMessage (status='rejected').
    Broadcasts the updated payload via WebSocket.
    """
    result = await db.execute(select(BloombergMessage).where(BloombergMessage.eventId == event_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.messageStatus = "rejected"
    await db.commit()
    await db.refresh(msg)

    payload = BloombergMessageResponse.model_validate(msg, from_attributes=True).model_dump(mode="json")
    await message_manager.broadcast_json({"type": "message_update", "payload": payload})

    return msg

# --- Set original LLM response ---
@router.put("/set-llm-response/{event_id}", response_model=BloombergMessageResponse)
async def set_llm_response(event_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Attach the original LLM JSON response to a BloombergMessage.
    When the LLM worker provides parsed data, mark messageStatus as 'received'.
    """
    result = await db.execute(
        select(BloombergMessage).where(BloombergMessage.eventId == event_id)
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # store the LLM response
    msg.original_llm_json = payload

    # update status -> received
    msg.messageStatus = "received"

    await db.commit()
    await db.refresh(msg)

    # broadcast update to WS clients
    updated_payload = BloombergMessageResponse.model_validate(
        msg, from_attributes=True
    ).model_dump(mode="json")
    await message_manager.broadcast_json(
        {"type": "message_update", "payload": updated_payload}
    )

    return msg

# --- Update isTarget field ---
@router.put("/update-target/{event_id}", response_model=BloombergMessageResponse)
async def update_target(event_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Update `isTarget` for a BloombergMessage.
    If the message is already approved, also update related Orders.
    """
    is_target = payload.get("isTarget")
    if is_target is None:
        raise HTTPException(status_code=400, detail="isTarget must be provided (true/false)")

    result = await db.execute(select(BloombergMessage).where(BloombergMessage.eventId == event_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.isTarget = bool(is_target)
    await db.commit()
    await db.refresh(msg)

    # --- Update related orders if message is approved ---
    if msg.messageStatus == "approved":
        await db.execute(
            update(Order)
            .where(Order.eventId == event_id)
            .values(isTarget=bool(is_target))
        )
        await db.commit()
        print(f"Updated related orders for eventId={event_id} with isTarget={is_target}")

    # --- Broadcast update to WebSocket clients ---
    payload = BloombergMessageResponse.model_validate(msg, from_attributes=True).model_dump(mode="json")
    await message_manager.broadcast_json({"type": "message_update", "payload": payload})

    return msg