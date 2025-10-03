import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from app.models import BloombergMessage, User

API_URL = "https://bgg-tester.onrender.com/messages"


async def fetch_and_process_messages(db: AsyncSession):
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(API_URL)
        resp.raise_for_status()
        data = resp.json()

    if not isinstance(data, dict):
        print(f"⚠️ Unexpected API shape: {type(data)}")
        return {"inserted": 0, "status": "bad format"}

    event = data
    event_id = event.get("eventId")
    inserted = 0

    for msg_obj in event.get("messages", []):
        msg_text = msg_obj.get("message")
        sender = msg_obj.get("sender", {})
        trader_uuid = str(sender.get("uuid")) if sender else None

        trader_alias = None
        trader_legal = None
        if trader_uuid:
            result = await db.execute(select(User).where(User.uuid == trader_uuid))
            user = result.scalar_one_or_none()
            if user:
                trader_alias = user.alias
                trader_legal = user.legalEntityShortName

        bloomberg_msg = {
            "eventId": event_id,
            "roomId": event.get("roomId"),
            "originalMessage": msg_text,
            "trader_uuid": trader_uuid,
            "trader_legalEntityShortName": trader_legal,
            "trader_alias": trader_alias,
            "original_llm_json": None,
            "current_json": None,
            "is_edited": False,
            "messageStatus": "received",
        }

        await db.execute(insert(BloombergMessage).values(bloomberg_msg))
        inserted += 1

    await db.commit()
    return {"inserted": inserted, "status": "received"}
