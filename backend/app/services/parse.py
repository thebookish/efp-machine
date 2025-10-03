import re
import json
import uuid
from typing import Optional
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

RUN_LINE_REGEX = re.compile(r"(?P<expiry>[A-Za-z]{3}\d{2})\s+(?P<bid>[0-9.]+)\s*/\s*(?P<ask>[0-9.]+)")
SINGLE_REGEX = re.compile(
    r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
    r"(?P<price>[0-9.]+)\s+.*?(?P<side>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
    re.IGNORECASE,
)


def parse_single_message(event: dict, msg_obj: dict) -> Optional[dict]:
    """
    Detect whether a Bloomberg chat message is trade/order related.
    If yes, return metadata (not an Order).
    If no, return None (ignore as normal chat).
    """

    msg_text = msg_obj.get("message", "").strip()
    if not msg_text:
        return None

    event_id = str(event.get("eventId")) if event.get("eventId") else str(uuid.uuid4())
    trader_uuid = str(msg_obj.get("sender", {}).get("uuid")) if msg_obj.get("sender") else None

    # --- PRICE RUN ---
    if "vs" in msg_text and RUN_LINE_REGEX.search(msg_text):
        return {
            "eventId": event_id,
            "message": msg_text,
            "trader_uuid": trader_uuid,
            "type": "PRICE_RUN"
        }

    # --- SINGLE TRADE ---
    match = SINGLE_REGEX.search(msg_text)
    if match:
        return {
            "eventId": event_id,
            "message": msg_text,
            "trader_uuid": trader_uuid,
            "type": "SINGLE"
        }

    # --- Fallback: AI classification ---
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Classify if this Bloomberg chat message is a trade/order or just normal chat."},
                {"role": "user", "content": f"Message: {msg_text}\nReply ONLY with 'ORDER' or 'CHAT'."},
            ],
        )
        label = resp.choices[0].message.content.strip().upper()
        if "ORDER" in label:
            return {
                "eventId": event_id,
                "message": msg_text,
                "trader_uuid": trader_uuid,
                "type": "AI_ORDER"
            }
        else:
            return None
    except Exception as e:
        print(f"⚠️ AI classification failed: {e}")
        return None
