from typing import Optional

WATCHPOINT_THRESHOLD = 0.75

EFP_ORDER = [
    'SX5E','SX5E CC','FTSE','DAX','SMI','MIB','CAC','IBEX','AEX','OMX','SX7E','SX7E CC'
]

def is_improvement(old: Optional[float], new: Optional[float], side: str) -> Optional[bool]:
    if old is None or new is None:
        return None
    if side == 'bid':
        if new >= 0 and old >= 0:
            return new > old
        if new < 0 and old < 0:
            return new > old
        if old >= 0 and new < 0:
            return False
        if old < 0 and new >= 0:
            return True
    if side == 'offer':
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
    cash_str = f"{cash_ref}" if cash_ref is not None else 'N/A'
    return f"{index} EFP traded at {price:.2f} in {lots} lots vs {index} cash {cash_str}"
