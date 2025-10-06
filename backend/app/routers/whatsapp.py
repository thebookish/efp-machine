import uuid
from app.services.whatsapp_client import send_whatsapp_message
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.deps import get_db
from app.models import BloombergMessage
from app.schemas import BloombergMessageResponse
from app.services.parse import parse_single_message
from .bloomberg_msg import message_manager  # reuse WS manager

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook that Twilio calls when a new WhatsApp message arrives.
    Instead of creating orders, store trade-related messages into BloombergMessage.
    - Generates a new UUID for eventId.
    - Extracts sender number without 'whatsapp:' prefix.
    """
    form = await request.form()
    from_number = form.get("From")  # e.g., 'whatsapp:+8801312345678'
    body = form.get("Body")

    if not body:
        return {"status": "ignored", "reason": "empty message"}

    # Clean sender UUID (remove 'whatsapp:' prefix)
    sender_uuid = from_number.replace("whatsapp:", "").strip() if from_number else None

    # Generate unique eventId for each incoming message
    event_id = str(uuid.uuid4())

    # Build fake event/msg for parse check
    fake_event = {"eventId": event_id}
    msg_obj = {
        "message": body,
        "timestamp": None,
        "sender": {"uuid": sender_uuid},
    }

    parsed_meta = parse_single_message(fake_event, msg_obj)

    if parsed_meta:
        # ✅ Store in BloombergMessage table
        new_msg = BloombergMessage(
            eventId=event_id,
            roomId="whatsapp",   # source identifier
            originalMessage=body,
            trader_uuid=sender_uuid,
            trader_legalEntityShortName=None,
            trader_alias=None,
            original_llm_json=None,
            current_json=None,
            is_edited=False,
            messageStatus="drafted",
            source="whatsapp",
        )

        db.add(new_msg)
        await db.commit()
        await db.refresh(new_msg)

        # ✅ Broadcast to WebSocket clients
        payload = BloombergMessageResponse.model_validate(new_msg, from_attributes=True).model_dump(mode="json")
        await message_manager.broadcast_json({"type": "message_new", "payload": payload})

        return {"status": "stored", "eventId": event_id, "sender_uuid": sender_uuid}

    return {"status": "ignored", "reason": "not an order message"}

@router.post("/send")
async def send_message(to: str, text: str):
    """
    Send WhatsApp message to a number.
    """
    res = await send_whatsapp_message(to, text)
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res["error"])
    return {"status": "sent", "sid": res["sid"]}