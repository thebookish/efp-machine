from fastapi import APIRouter, HTTPException
from app.services.slack_client import send_slack_message
from app.services.whatsapp_client import send_whatsapp_message

router = APIRouter(prefix="/api/send", tags=["send"])

@router.post("/")
async def send_message(payload: dict):
    """
    Send one or multiple messages to Slack and/or WhatsApp.
    Payload:
    {
      "text": "hello world",
      "slack_targets": ["U12345", "#general"],
      "whatsapp_numbers": ["+8801823564420", "+8801906786163"]
    }
    """
    try:
        text = payload.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="Message text is required")

        results = {"slack": [], "whatsapp": []}

        # Slack broadcast
        if payload.get("slack_targets"):
            for target in payload["slack_targets"]:
                try:
                    res = await send_slack_message(target, text)
                    results["slack"].append({target: res})
                except Exception as e:
                    results["slack"].append({target: {"ok": False, "error": str(e)}})

        # WhatsApp broadcast
        if payload.get("whatsapp_numbers"):
            for number in payload["whatsapp_numbers"]:
                try:
                    res = await send_whatsapp_message(number, text)
                    results["whatsapp"].append({number: res})
                except Exception as e:
                    results["whatsapp"].append({number: {"ok": False, "error": str(e)}})

        return {"reply": "Broadcast completed", "results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send failed: {e}")
