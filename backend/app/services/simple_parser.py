import re
from typing import Optional, Dict

def simple_parse_message(msg: str) -> Optional[Dict]:
    """
    Simple regex-based parser for order messages.
    Handles messages like:
      "SX5E DEC26 TRF 55 we can buy vs 3.74"
      "We can sell 1 DAX Mar26 TRF at 100 vs 2.25"
    """

    if not msg:
        return None

    msg = msg.strip()

    # Pattern 1: SYMBOL EXPIRY TRF PRICE ... buy/sell ... vs BASIS
    pattern1 = re.compile(
        r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Za-z0-9]+)\s+TRF\s+"
        r"(?P<price>\d+(?:\.\d+)?)\s+.*?(?P<buySell>buy|sell)\s+.*?vs\s+(?P<basis>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    # Pattern 2: We can buy/sell SYMBOL EXPIRY TRF at PRICE vs BASIS
    pattern2 = re.compile(
        r"we can\s+(?P<buySell>buy|sell)\s+\d*\s*"
        r"(?P<contractId>[A-Z0-9]+)\s+(?P<expiryDate>[A-Za-z0-9]+)\s+TRF\s+"
        r"(?:at\s+)?(?P<price>\d+(?:\.\d+)?)\s+vs\s+(?P<basis>\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    for pattern in (pattern1, pattern2):
        m = pattern.search(msg)
        if m:
            return {
                "contractId": m.group("contractId").upper(),
                "expiryDate": m.group("expiryDate").upper(),
                "buySell": m.group("buySell").upper(),
                "price": float(m.group("price")),
                "basis": float(m.group("basis")),
            }

    return None
