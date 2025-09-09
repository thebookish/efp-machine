import json
import re
import uuid
from app.schemas import OrderCreate
from app.config import settings
from openai import OpenAI

# OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def parse_bbg_message(event: dict) -> OrderCreate | None:
    """
    Parse Bloomberg-style message into OrderCreate schema.

    Example message formats:
      "SX5E DEC25 TRF 61 we can sell vs 3.75"
      "We can buy 1 SX5E DEC25 TRF at 62 vs 3.80"

    Strategy:
    1. Try strict regex parsing (fast).
    2. If regex fails, fallback to AI-based JSON extraction.
    """
    msg = event.get("message", "").strip()
    if not msg:
        return None

    # --- 1. Regex parsing ---
    pattern = re.compile(
        r"(?P<symbol>[A-Z0-9]+)\s+(?P<expiry>[A-Z0-9]+)\s+TRF\s+"
        r"(?P<price>[0-9.]+)\s+.*?(?P<side>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
        re.IGNORECASE,
    )
    match = pattern.search(msg)

    if match:
        return OrderCreate(
            client_provided_id=str(event.get("eventId", uuid.uuid4())),
            symbol=match.group("symbol").upper(),
            expiry=match.group("expiry").upper(),
            side=match.group("side").upper(),
            quantity=1.0,  # default, Bloomberg doesn’t send lots
            price=float(match.group("price")),
            basis=float(match.group("basis")),
        )

    # --- 2. AI fallback parsing ---
    prompt = f"""
    Extract structured trade info from the following message:

    Message: "{msg}"

    Return a JSON object with fields:
    - symbol (string, e.g., SX5E)
    - expiry (string, e.g., DEC25)
    - side (BUY or SELL)
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
            client_provided_id=str(event.get("eventId", uuid.uuid4())),
            symbol=parsed["symbol"].upper(),
            expiry=parsed["expiry"].upper(),
            side=parsed["side"].upper(),
            quantity=1.0,
            price=float(parsed["price"]),
            basis=float(parsed["basis"]),
        )
    except Exception as e:
        print(f"⚠️ AI parsing failed for message='{msg}': {e}")
        return None
