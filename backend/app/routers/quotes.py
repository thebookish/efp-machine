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
        {"client": "C4", "bid": 9.15, "offer": 9.7},
        {"client": "C5", "bid": 9.28, "offer": 9.62},
    ],
    "FTSE": [
        {"client": "C1", "bid": 22.1, "offer": 22.7},
        {"client": "C2", "bid": 22.3, "offer": 22.8},
        {"client": "C3", "bid": 22.2, "offer": 22.6},
        {"client": "C4", "bid": 22.35, "offer": 22.75},
        {"client": "C5", "bid": 22.25, "offer": 22.9},
    ],
    "DAX": [
        {"client": "C1", "bid": 41.0, "offer": 44.2},
        {"client": "C2", "bid": 41.5, "offer": 43.8},
        {"client": "C3", "bid": 40.9, "offer": 44.0},
        {"client": "C4", "bid": 41.2, "offer": 43.9},
        {"client": "C5", "bid": 41.4, "offer": 44.1},
    ],
    "SMI": [
        {"client": "C1", "bid": -10.2, "offer": -8.9},
        {"client": "C2", "bid": -10.0, "offer": -9.0},
        {"client": "C3", "bid": -9.8, "offer": -8.75},
        {"client": "C4", "bid": -10.1, "offer": -8.8},
        {"client": "C5", "bid": -9.9, "offer": -8.7},
    ],
    "MIB": [
        {"client": "C1", "bid": 69.0, "offer": 72.5},
        {"client": "C2", "bid": 70.0, "offer": 72.2},
        {"client": "C3", "bid": 69.5, "offer": 72.0},
        {"client": "C4", "bid": 70.2, "offer": 73.0},
        {"client": "C5", "bid": 69.8, "offer": 72.3},
    ],
    "CAC": [
        {"client": "C1", "bid": 13.0, "offer": 14.5},
        {"client": "C2", "bid": 13.2, "offer": 14.3},
        {"client": "C3", "bid": 12.9, "offer": 14.4},
        {"client": "C4", "bid": 13.1, "offer": 14.6},
        {"client": "C5", "bid": 13.15, "offer": 14.55},
    ],
    "IBEX": [
        {"client": "C1", "bid": 18.5, "offer": 20.0},
        {"client": "C2", "bid": 18.7, "offer": 19.9},
        {"client": "C3", "bid": 18.6, "offer": 19.95},
        {"client": "C4", "bid": 18.8, "offer": 20.1},
        {"client": "C5", "bid": 18.55, "offer": 19.85},
    ],
    "AEX": [
        {"client": "C1", "bid": 0.9, "offer": 1.05},
        {"client": "C2", "bid": 0.92, "offer": 1.04},
        {"client": "C3", "bid": 0.91, "offer": 1.06},
        {"client": "C4", "bid": 0.89, "offer": 1.03},
        {"client": "C5", "bid": 0.93, "offer": 1.07},
    ],
    "OMX": [
        {"client": "C1", "bid": 4.2, "offer": 4.4},
        {"client": "C2", "bid": 4.1, "offer": 4.35},
        {"client": "C3", "bid": 4.25, "offer": 4.38},
        {"client": "C4", "bid": 4.15, "offer": 4.42},
        {"client": "C5", "bid": 4.18, "offer": 4.36},
    ],
    "SX7E": [
        {"client": "C1", "bid": 0.28, "offer": 0.32},
        {"client": "C2", "bid": 0.3, "offer": 0.33},
        {"client": "C3", "bid": 0.29, "offer": 0.31},
        {"client": "C4", "bid": 0.27, "offer": 0.34},
        {"client": "C5", "bid": 0.28, "offer": 0.35},
    ],
    "SX7E CC": [
        {"client": "C1", "bid": 0.15, "offer": 0.2},
        {"client": "C2", "bid": 0.16, "offer": 0.21},
        {"client": "C3", "bid": 0.14, "offer": 0.22},
        {"client": "C4", "bid": 0.17, "offer": 0.19},
        {"client": "C5", "bid": 0.15, "offer": 0.2},
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
