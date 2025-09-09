import json
import re
import uuid
from typing import Optional
from openai import OpenAI

from app.schemas import OrderCreate
from app.config import settings

# OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def parse_bbg_message(event: dict) -> Optional[OrderCreate]:
    """
    Parse Bloomberg-style message into OrderCreate schema.

    Example message formats:
      "SX5E DEC25 TRF 61 we can sell vs 3.75"
      "We can buy 1 SX5E DEC25 TRF at 62 vs 3.80"

    Output fields:
      message, orderType, buySell, quantity, price, basis,
      strategyDisplayName, contractId, expiryDate
    """

    # Extract raw message from event (works for both flat + nested JSONs)
    msg = event.get("message")
    if not msg and "messages" in event and event["messages"]:
        msg = event["messages"][0].get("message")

    if not msg:
        return None

    msg = msg.strip()

    # --- 1. Regex parsing ---
    regex_patterns = [
        # Format: SYMBOL EXPIRY TRF PRICE we can buy/sell vs BASIS
        re.compile(
            r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
            r"(?P<price>[0-9.]+)\s+.*?(?P<buySell>buy|sell)\s+.*?(?P<basis>[0-9.]+)",
            re.IGNORECASE,
        ),
        # Format: we can buy 1 SYMBOL EXPIRY TRF at PRICE vs BASIS
        re.compile(
            r"we can\s+(?P<buySell>buy|sell)\s+[0-9.]*\s*"
            r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Z0-9]+)\s+TRF\s+"
            r"(?:at\s+)?(?P<price>[0-9.]+)\s+vs\s+(?P<basis>[0-9.]+)",
            re.IGNORECASE,
        ),
    ]

    for pattern in regex_patterns:
        match = pattern.search(msg)
        if match:
            return OrderCreate(
                message=msg,
                orderType="SINGLE",
                buySell=match.group("buySell").upper(),
                quantity=1.0,  # default
                price=float(match.group("price")),
                basis=float(match.group("basis")),
                strategyDisplayName="TRF",
                contractId=match.group("contractId").upper(),
                expiryDate=match.group("expiryDate").upper(),
            )

    # --- 2. AI fallback parsing ---
    prompt = f"""
    Extract structured trade info from the following message:

    Message: "{msg}"

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
            message=msg,
            orderType="SINGLE",
            buySell=parsed["buySell"].upper(),
            quantity=1.0,
            price=float(parsed["price"]),
            basis=float(parsed["basis"]),
            strategyDisplayName="TRF",
            contractId=parsed["contractId"].upper(),
            expiryDate=parsed["expiryDate"].upper(),
        )
    except Exception as e:
        print(f"⚠️ AI parsing failed for message='{msg}': {e}")
        return None
