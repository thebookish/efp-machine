import re
import uuid
from app.models import Order
from app.schemas import OrderCreate

def parse_bbg_message(event: dict) -> OrderCreate | None:
    """
    Parse Bloomberg message to OrderCreate schema
    Example message:
      "SX5E DEC25 TRF 61 we can sell vs 3.75"
    """
    msg = event["message"]

    # Regex to capture format "<symbol> TRF <qty> we can (buy|sell) vs <price>"
    pattern = re.compile(
        r"(?P<symbol>[A-Z0-9\s]+) TRF (?P<qty>\d+) we can (?P<side>buy|sell) vs (?P<price>[0-9.]+)",
        re.IGNORECASE,
    )
    match = pattern.search(msg)
    if not match:
        return None

    side = match.group("side").upper()
    return OrderCreate(
        client_provided_id=str(event["eventId"]),  # use Bloomberg event id
        symbol=match.group("symbol").strip(),
        side=side,
        quantity=float(match.group("qty")),
        price=float(match.group("price")),
    )
