import json
import re
import uuid
from app.schemas import OrderCreate
from app.config import settings
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def parse_bbg_message(event: dict) -> OrderCreate | None:
    """
    Parse Bloomberg message into OrderCreate schema.
    Uses regex fallback and AI for free-text variations.
    """
    msg = event["message"]

    # --- 1. Try Regex First (fast and strict) ---
    pattern = re.compile(
        r"(?P<symbol>[A-Z0-9]+)\s+(?P<expiry>[A-Z0-9]+)\s+TRF\s+(?P<price>[0-9.]+)\s+.*?(?P<side>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
        re.IGNORECASE,
    )
    match = pattern.search(msg)
    if match:
        return OrderCreate(
            client_provided_id=str(event.get("eventId", uuid.uuid4())),
            symbol=f"{match.group('symbol').upper()} {match.group('expiry').upper()}",
            side=match.group("side").upper(),
            quantity=1.0,
            price=float(match.group("price")),
            basis=float(match.group("basis")),
        )

    # --- 2. If regex fails → Ask AI to normalize ---
    prompt = f"""
    Extract structured trade info from the following message:

    Message: "{msg}"

    Return JSON with fields:
    - symbol (string, e.g., SX5E)
    - expiry (string, e.g., DEC25)
    - side (BUY or SELL)
    - price (float, TRF spread, e.g., 61)
    - basis (float, vs value, e.g., 3.75)
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a trade parser."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        data = resp.choices[0].message.content
        parsed = json.loads(data)

        return OrderCreate(
            client_provided_id=str(event.get("eventId", uuid.uuid4())),
            symbol=f"{parsed['symbol'].upper()} {parsed['expiry'].upper()}",
            side=parsed["side"].upper(),
            quantity=1.0,
            price=float(parsed["price"]),
            basis=float(parsed["basis"]),
        )
    except Exception as e:
        print(f"AI parsing failed: {e}")
        return None
