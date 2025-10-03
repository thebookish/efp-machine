from http.client import HTTPException
from app.services.whatsapp_client import send_whatsapp_message
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.services.order_ingest import enqueue_order
from app.services.parse import parse_single_message

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook that Twilio calls when a new WhatsApp message arrives.
    """
    form = await request.form()
    from_number = form.get("From")
    body = form.get("Body")

    # Fake event/msg like Slack handler
    fake_event = {"eventId": from_number}
    msg_obj = {
        "message": body,
        "timestamp": None,
        "sender": {"uuid": from_number},
    }

    parsed_orders = parse_single_message(fake_event, msg_obj)
    if parsed_orders:
        if not isinstance(parsed_orders, list):
            parsed_orders = [parsed_orders]
        for order in parsed_orders:
            await enqueue_order(order)
        return {"status": "accepted", "queued": len(parsed_orders)}

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