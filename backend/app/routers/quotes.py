# backend/app/routers/quotes.py
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter(prefix="/api/quotes", tags=["quotes"])

# Dummy quotes (simulate 10 clients)
DUMMY_QUOTES = {
    "SX5E": [
        {"client": "C1", "bid": 9.2, "offer": 9.6},
        {"client": "C2", "bid": 9.25, "offer": 9.55},
        {"client": "C3", "bid": 9.3, "offer": 9.65},
    ],
    "DAX": [
        {"client": "C4", "bid": 41.0, "offer": 44.2},
        {"client": "C5", "bid": 41.5, "offer": 43.8},
        {"client": "C6", "bid": 40.9, "offer": 44.0},
    ],
}

@router.get("/bbo/{index}")
async def get_bbo(index: str):
    index = index.upper()
    if index not in DUMMY_QUOTES:
        return {"detail": f"No quotes for {index}"}

    quotes = DUMMY_QUOTES[index]
    best_bid = max(quotes, key=lambda x: x["bid"])
    best_offer = min(quotes, key=lambda x: x["offer"])

    return {
        "index": index,
        "best_bid": best_bid["bid"],
        "best_bid_client": best_bid["client"],
        "best_offer": best_offer["offer"],
        "best_offer_client": best_offer["client"],
    }
