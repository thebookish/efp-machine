# backend/app/services/theory.py
from typing import Optional, Tuple

def compute_theoretical(index: str, bid: float, offer: float, cash_ref: float):
    mid = (bid + offer) / 2
    # Add offset based on cash_ref to force divergence
    offset = round(cash_ref * 0.0002, 2)  # e.g. 4200 * 0.0002 = 0.84
    theo_bid = round(mid - offset, 2)
    theo_offer = round(mid + offset, 2)
    return theo_bid, theo_offer


def check_watchpoint(
    actual_bid: Optional[float],
    actual_offer: Optional[float],
    theo_bid: Optional[float],
    theo_offer: Optional[float]
) -> bool:
    """
    Flag a watchpoint if deviation > 0.75pts between actual and theoretical.
    """
    if None in (actual_bid, actual_offer, theo_bid, theo_offer):
        return False
    return (
        abs(actual_bid - theo_bid) > 0.75
        or abs(actual_offer - theo_offer) > 0.75
    )
