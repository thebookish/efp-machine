# backend/app/services/efp_protocol.py
from typing import Optional
from datetime import date, timedelta

# from app.services.theory import compute_theoretical

WATCHPOINT_THRESHOLD = 0.75

# Order of instruments in published runs
EFP_ORDER = [
    "SX5E", "SX5E CC", "FTSE", "DAX", "SMI", "MIB",
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC"
]


# ----------------- Price movement rules -----------------
def is_improvement(old: Optional[float], new: Optional[float], side: str) -> Optional[bool]:
    if old is None or new is None:
        return None
    if side == "bid":
        if new >= 0 and old >= 0:
            return new > old
        if new < 0 and old < 0:
            return new > old
        if old >= 0 and new < 0:
            return False
        if old < 0 and new >= 0:
            return True
    if side == "offer":
        if new >= 0 and old >= 0:
            return new < old
        if new < 0 and old < 0:
            return new < old
        if old >= 0 and new < 0:
            return True
        if old < 0 and new >= 0:
            return False
    return None


def is_worsening(old: Optional[float], new: Optional[float], side: str) -> Optional[bool]:
    imp = is_improvement(old, new, side)
    return (imp is not None) and (imp is False)


def require_cash_ref_on_update(old_cash: Optional[float], provided_cash: Optional[float]) -> bool:
    return provided_cash is None


def format_recap(index: str, price: float, lots: int, cash_ref: Optional[float]) -> str:
    cash_str = f"{cash_ref}" if cash_ref is not None else "N/A"
    return f"{index} EFP traded at {price:.2f} in {lots} lots vs {index} cash {cash_str}"


# ----------------- Watchpoint logic -----------------

def deviation_watchpoint(r) -> bool:
    """Return True if actual bid/offer deviates from theoretical by >0.75"""
    if r.bid is None or r.offer is None or r.cash_ref is None:
        return False

    theo_bid, theo_offer = compute_theoretical(r.index_name, r.bid, r.offer, r.cash_ref)

    if theo_bid is None or theo_offer is None:
        return False

    return (
        abs(r.bid - theo_bid) > 0.75 or
        abs(r.offer - theo_offer) > 0.75
    )

# ----------------- Expiry classification -----------------
QUARTERLY = {"SX5E", "SX5E CC", "FTSE", "DAX", "SMI", "MIB", "SX7E", "SX7E CC"}
MONTHLY = {"CAC", "IBEX", "AEX", "OMX"}


def third_friday(year: int, month: int) -> date:
    """Return the 3rd Friday of a given month."""
    d = date(year, month, 1)
    # find first Friday
    while d.weekday() != 4:  # 0=Mon, 4=Fri
        d += timedelta(days=1)
    # add 14 days → 3rd Friday
    return d + timedelta(days=14)



def classify_expiry_status(index: str, today: date) -> dict:
    """Return expiry classification and expiry date for an index."""
    month = today.month
    year = today.year

    expiry_date = None
    status = "Pending"

    # Quarterly → only March, June, Sept, Dec
    if index in QUARTERLY:
        if month not in (3, 6, 9, 12):
            return {"index": index, "status": "Pending", "expiry_date": None}
    elif index in MONTHLY:
        pass  # applies to all months
    else:
        return {"index": index, "status": "Pending", "expiry_date": None}

    expiry_date = third_friday(year, month)

    if today > expiry_date:
        status = "Expired"
    elif today == expiry_date:
        status = "In expiry window"
    else:
        status = "Pending"

    return {
        "index": index,
        "status": status,
        "expiry_date": expiry_date.isoformat(),
    }
