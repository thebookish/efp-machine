import re
import json
import uuid
from typing import Optional, List
from app.schemas import OrderCreate
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

RUN_LINE_REGEX = re.compile(r"(?P<expiry>[A-Za-z]{3}\d{2})\s+(?P<bid>[0-9.]+)\s*/\s*(?P<ask>[0-9.]+)")
SINGLE_REGEX = re.compile(
    r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
    r"(?P<price>[0-9.]+)\s+.*?(?P<side>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
    re.IGNORECASE,
)


def parse_single_message(event: dict, msg_obj: dict) -> Optional[List[OrderCreate]]:
    msg_text = msg_obj.get("message", "").strip()
    if not msg_text:
        return None

    event_id = str(event.get("eventId")) if event.get("eventId") else str(uuid.uuid4())
    trader_uuid = str(msg_obj.get("sender", {}).get("uuid")) if msg_obj.get("sender") else None

    linked_id = event_id  # ✅ group orders by eventId

    orders: List[OrderCreate] = []

    if "vs" in msg_text and RUN_LINE_REGEX.search(msg_text):
        basis_match = re.search(r"vs\s*([0-9.+-]+)", msg_text)
        basis = float(basis_match.group(1)) if basis_match else 0.0

        contract_match = re.match(r"([A-Z0-9]+)\s+TRF", msg_text)
        contract_id = contract_match.group(1).upper() if contract_match else "UNKNOWN"

        for run in RUN_LINE_REGEX.finditer(msg_text):
            expiry = run.group("expiry").upper()
            bid = float(run.group("bid"))
            ask = float(run.group("ask"))

            orders.append(OrderCreate(
                eventId=event_id,
                linkedOrderID=linked_id,
                message=msg_text,
                expiryDate=expiry,
                strategyID=None,
                contractId=contract_id,
                side="BUY",
                price=bid,
                basis=basis,
                traderUuid=trader_uuid,
            ))
            orders.append(OrderCreate(
                eventId=event_id,
                linkedOrderID=linked_id,
                message=msg_text,
                expiryDate=expiry,
                strategyID=None,
                contractId=contract_id,
                side="SELL",
                price=ask,
                basis=basis,
                traderUuid=trader_uuid,
            ))
        return orders

    match = SINGLE_REGEX.search(msg_text)
    if match:
        return [OrderCreate(
            eventId=event_id,
            linkedOrderID=linked_id,
            message=msg_text,
            expiryDate=match.group("expiryDate").upper(),
            strategyID=None,
            contractId=match.group("contractId").upper(),
            side=match.group("side").upper(),
            price=float(match.group("price")),
            basis=float(match.group("basis")),
            traderUuid=trader_uuid,
        )]

    # fallback to AI
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise trade parser."},
                {"role": "user", "content": f"Parse: {msg_text}"},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(resp.choices[0].message.content)
        return [OrderCreate(
            eventId=event_id,
            linkedOrderID=linked_id,
            message=msg_text,
            expiryDate=parsed["expiryDate"].upper(),
            strategyID=None,
            contractId=parsed["contractId"].upper(),
            side=parsed["buySell"].upper(),
            price=float(parsed["price"]),
            basis=float(parsed["basis"]),
            traderUuid=trader_uuid,
        )]
    except Exception as e:
        print(f"⚠️ AI parsing failed: {e}")
        return None
