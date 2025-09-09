import re
from app.schemas import OrderCreate

def parse_bbg_message(event: dict) -> OrderCreate | None:
    """
    Parse Bloomberg message into OrderCreate schema.
    Example:
      "SX5E DEC25 TRF 61 we can sell vs 3.75"
    """
    msg = event["message"]

    # Regex: SYMBOL + EXPIRY + TRF + PRICE + SIDE + BASIS
    pattern = re.compile(
        r"^(?P<symbol>[A-Z0-9]+)\s+(?P<expiry>[A-Z0-9]+)\s+TRF\s+(?P<price>[0-9.]+)\s+we can\s+(?P<side>buy|sell)\s+vs\s+(?P<basis>[0-9.]+)",
        re.IGNORECASE,
    )
    match = pattern.search(msg)
    if not match:
        return None

    side = match.group("side").upper()
    symbol = match.group("symbol").upper()
    expiry = match.group("expiry").upper()
    price = float(match.group("price"))
    basis = float(match.group("basis"))

    return OrderCreate(
        client_provided_id=str(event["eventId"]),  # Bloomberg event ID
        symbol=f"{symbol} {expiry}",              # combine symbol + expiry
        side=side,
        basis=basis,                             # dummy quantity (not in message)
        price=price,                          # TRF spread price
    )
