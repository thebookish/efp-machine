import httpx
from app.services.parse import parse_single_message
from app.services.order_ingest import enqueue_order

API_URL = "https://bgg-tester.onrender.com/messages"

async def fetch_and_process_messages():
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(API_URL)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, dict):
        print(f"⚠️ Unexpected API shape: {type(data)}")
        return {"queued": 0, "status": "bad format"}

    inserted = 0
    event = data
    event_id = event.get("eventId")

    for msg_obj in event.get("messages", []):
        print(f"🔎 Parsing message for eventId={event_id}: {msg_obj.get('message')}")
        parsed_orders = parse_single_message(event, msg_obj)

        if parsed_orders:
            for order in parsed_orders:  # ✅ handle multiple orders
                await enqueue_order(order)
                inserted += 1
            print(f"✅ Parsed {len(parsed_orders)} order(s) for eventId={event_id}")
        else:
            print(f"❌ Failed to parse message for eventId={event_id}: {msg_obj}")

    return {"queued": inserted, "status": "accepted"}
