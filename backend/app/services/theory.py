from typing import Tuple

def compute_theoretical(bid: float | None, offer: float | None, cash_ref: float | None) -> Tuple[float, float]:
    if cash_ref is None:
        cash_ref = 0.0
    if bid is not None and offer is not None:
        mid = (bid + offer) / 2
    elif bid is not None:
        mid = bid
    elif offer is not None:
        mid = offer
    else:
        mid = 0.0
    theory_bid = round(mid - 0.25, 2)
    theory_offer = round(mid + 0.25, 2)
    return theory_bid, theory_offer
