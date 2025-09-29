import re
import json
import uuid
from typing import Optional, List
from app.schemas import OrderCreate
from openai import OpenAI
from app.config import settings

# OpenAI client (for fallback parsing)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Regex for price runs like: Dec25 56/58
RUN_LINE_REGEX = re.compile(
    r"(?P<expiry>[A-Za-z]{3}\d{2})\s+(?P<bid>[0-9.]+)\s*/\s*(?P<ask>[0-9.]+)"
)

# Regex for single trades
SINGLE_REGEX = re.compile(
    r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
    r"(?P<price>[0-9.]+)\s+.*?(?P<buySell>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
    re.IGNORECASE,
)


def parse_single_message(event: dict, msg_obj: dict) -> Optional[List[OrderCreate]]:
    """
    Parse one chat message into one or more OrderCreate objects.
    Supports:
    - Price run messages (multiple expiries, bid/ask pairs).
    - Single trade messages (regex or AI fallback).
    """
    msg_text = msg_obj.get("message", "").strip()
    if not msg_text:
        return None

    event_id = str(event.get("eventId")) if event.get("eventId") else None
    ts = msg_obj.get("timestamp")
    sender_uuid = str(msg_obj.get("sender", {}).get("uuid")) if msg_obj.get("sender") else None

    # --- Detect and parse PRICE RUN ---
    if "vs" in msg_text and RUN_LINE_REGEX.search(msg_text):
        # Extract basis (after "vs")
        basis_match = re.search(r"vs\s*([0-9.+-]+)", msg_text)
        basis = float(basis_match.group(1)) if basis_match else None

        # ContractId (e.g. SX5E)
        contract_match = re.match(r"([A-Z0-9]+)\s+TRF", msg_text)
        contract_id = contract_match.group(1).upper() if contract_match else None

        # Shared linkedOrderID for the whole run
        run_id = str(uuid.uuid4())

        orders: List[OrderCreate] = []
        for run in RUN_LINE_REGEX.finditer(msg_text):
            expiry = run.group("expiry").upper()
            bid = float(run.group("bid"))
            ask = float(run.group("ask"))

            # BUY order from bid
            orders.append(OrderCreate(
                eventId=event_id,
                message=msg_text,
                message_timestamp=ts,
                sender_uuid=sender_uuid,
                requester_uuid=None,
                orderType="PRICE_RUN",
                state="ACTIVE",
                buySell="BUY",
                price=bid,
                basis=basis,
                contractId=contract_id,
                expiryDate=expiry,
                linkedOrderID=run_id,   # ✅ all orders in this run share this ID
            ))

            # SELL order from ask
            orders.append(OrderCreate(
                eventId=event_id,
                message=msg_text,
                message_timestamp=ts,
                sender_uuid=sender_uuid,
                requester_uuid=None,
                orderType="PRICE_RUN",
                state="ACTIVE",
                buySell="SELL",
                price=ask,
                basis=basis,
                contractId=contract_id,
                expiryDate=expiry,
                linkedOrderID=run_id,   # ✅ all orders in this run share this ID
            ))

        return orders

    # --- Else: fall back to SINGLE TRADE regex ---
    match = SINGLE_REGEX.search(msg_text)
    if match:
        return [
            OrderCreate(
                eventId=event_id,
                message=msg_text,
                message_timestamp=ts,
                sender_uuid=sender_uuid,
                requester_uuid=None,
                orderType="SINGLE",
                state="ACTIVE",
                buySell=match.group("buySell").upper(),
                price=float(match.group("price")),
                basis=float(match.group("basis")),
                contractId=match.group("contractId").upper(),
                expiryDate=match.group("expiryDate").upper(),
                linkedOrderID=None,  # singles not grouped
            )
        ]
    # --- AI fallback (only if looks trade-related) ---
    # Strict filter: only try AI if contains TRF or EFP
    if not any(keyword in msg_text.upper() for keyword in ["TRF", "EFP"]):
        return None  # 🚫 Ignore normal chat
    prompt = f"""
    Extract structured trade info from the following message:

    Message: "{msg_text}"

    Return JSON with:
    - contractId (string, e.g., SX5E)
    - expiryDate (string, e.g., DEC25)
    - buySell (BUY or SELL)
    - price (float)
    - basis (float)
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

        return [
            OrderCreate(
                eventId=event_id,
                message=msg_text,
                message_timestamp=ts,
                sender_uuid=sender_uuid,
                requester_uuid=None,
                orderType="SINGLE",
                state="ACTIVE",
                buySell=parsed["buySell"].upper(),
                price=float(parsed["price"]),
                basis=float(parsed["basis"]),
                contractId=parsed["contractId"].upper(),
                expiryDate=parsed["expiryDate"].upper(),
                linkedOrderID=None,
            )
        ]
    except Exception as e:
        print(f"⚠️ AI parsing failed for '{msg_text}': {e}")
        return None
