import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import EfpRun, Recap
from app.services.efp_protocol import deviation_watchpoint, classify_expiry_status
from app.services.theory import compute_theoretical
from app.deps import AsyncSessionLocal

scheduler = AsyncIOScheduler(timezone="Europe/London")

last_prediction = None

async def publish_prediction():
    async with AsyncSessionLocal() as session:
        global last_prediction
        # 1. Get prior-day closes or current run
        result = await session.execute(select(EfpRun))
        rows = result.scalars().all()
        # If no cash_ref, just assume placeholder values
        efp_predictions = []
        for r in rows:
            mid = (r.bid + r.offer) / 2 if r.bid is not None and r.offer is not None else 0.0
            theo_bid, theo_offer = compute_theoretical(r.index_name, r.bid or 0, r.offer or 0, r.cash_ref or 0)
            efp_predictions.append({
                "index_name": r.index_name,
                "bid": r.bid,
                "offer": r.offer,
                "cash_ref": r.cash_ref,
                "theo_bid": theo_bid,
                "theo_offer": theo_offer,
                "watchpoint": deviation_watchpoint(r),
                "expiry": classify_expiry_status(r.index_name, datetime.today().date())
            })

        # 2. Predict TRF run for SX5E
        sx5e = next((row for row in efp_predictions if row["index_name"] == "SX5E"), None)
        trf_mid = (sx5e["bid"] + sx5e["offer"]) / 2 if sx5e else 0.0
        trf_run = {
            "index": "SX5E TRF",
            "basis": round(trf_mid, 2),
        }

        # 3. Get prior-day recaps
        recaps = await session.execute(select(Recap).order_by(Recap.created_at.desc()).limit(10))
        recap_list = [{
            "index_name": r.index_name,
            "recap_text": r.recap_text,
            "created_at": r.created_at.isoformat(),
        } for r in recaps.scalars()]

        # TODO: broadcast via websocket
        payload = {
            "predicted_run": efp_predictions,
            "trf_run": trf_run,
            "recaps": recap_list,
            "timestamp": datetime.now().isoformat()
        }
        last_prediction = payload
        print("🔮 Prediction Published:", payload)

        # In future → broadcast to clients (new WS channel)

def get_last_prediction():
    """Return the most recent prediction payload or None."""
    return last_prediction

def start_scheduler():
    scheduler.add_job(publish_prediction, "cron", hour=7, minute=50)
    scheduler.start()

