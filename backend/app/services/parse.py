import json
import re
from typing import Optional
from openai import OpenAI
from app.schemas import OrderCreate
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

regex_patterns = [
    re.compile(
        r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
        r"(?P<price>[0-9.]+)\s+.*?(?P<buySell>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"we can\s+(?P<buySell>buy|sell)\s+[0-9.]*\s*"
        r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
        r"(?:at\s+)?(?P<price>[0-9.]+)\s+vs\s+(?P<basis>[0-9.]+)",
        re.IGNORECASE,
    ),
]


def parse_single_message(event: dict, msg_obj: dict) -> Optional[OrderCreate]:
    print(f"📥 parsing order:")
    """
    Parse a single message inside an event into an OrderCreate object.
    """
    msg_text = msg_obj.get("message")
    if not msg_text:
        return None
    msg_text = msg_text.strip()

    # Metadata
    event_id = str(event.get("eventId")) if event.get("eventId") else None
    ts = msg_obj.get("timestamp")
    sender_uuid = str(msg_obj.get("sender", {}).get("uuid")) if msg_obj.get("sender") else None

    # Regex parsing
    for pattern in regex_patterns:
        match = pattern.search(msg_text)
        if match:
            return OrderCreate(
                eventId=event_id,
                message=msg_text,
                message_timestamp=ts,
                sender_uuid=sender_uuid,
                requester_uuid=None,
                orderType="price run",
                state="ACTIVE",
                buySell=match.group("buySell").upper(),
                price=float(match.group("price")),
                basis=float(match.group("basis")),
                contractId=match.group("contractId").upper(),
                expiryDate=match.group("expiryDate").upper(),
            )

    # AI fallback
    prompt = f"""
    Extract structured trade info from the following message:

    Message: "{msg_text}"

    Return a JSON object with fields:
    - contractId (string, e.g., SX5E)
    - expiryDate (string, e.g., DEC25)
    - buySell (BUY or SELL)
    - price (float, TRF spread, e.g., 61)
    - basis (float, vs value, e.g., 3.75)
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise trade parser."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(resp.choices[0].message.content)

        return OrderCreate(
            eventId=event_id,
            message=msg_text,
            message_timestamp=ts,
            sender_uuid=sender_uuid,
            requester_uuid=None,
            orderType="price run",
            state="ACTIVE",
            buySell=parsed["buySell"].upper(),
            price=float(parsed["price"]),
            basis=float(parsed["basis"]),
            contractId=parsed["contractId"].upper(),
            expiryDate=parsed["expiryDate"].upper(),
        )
    except Exception as e:
        print(f"⚠️ AI parsing failed for message='{msg_text}': {e}")
        return None
