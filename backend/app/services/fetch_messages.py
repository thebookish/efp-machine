import httpx
from app.services.parse import parse_bbg_message
from app.services.order_ingest import enqueue_order
from app.schemas import OrderCreate

API_URL = "https://bgg-tester.onrender.com/messages"


async def fetch_and_process_messages():
    """
    Fetch messages from the external API, parse them, and enqueue.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(API_URL)
        resp.raise_for_status()
        events = resp.json()

    inserted = 0
    for ev in events:
        parsed: OrderCreate | None = parse_bbg_message(ev)
        if parsed:
            await enqueue_order(parsed)
            inserted += 1

    return {"queued": inserted, "status": "accepted"}
