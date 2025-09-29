from fastapi import APIRouter, Request
import json

router = APIRouter(prefix="/api/slack", tags=["slack"])

@router.post("/events")
async def slack_events(request: Request):
    data = await request.json()

    # Slack URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data["challenge"]}

    # Handle message events
    if data.get("type") == "event_callback":
        event = data["event"]
        if event.get("type") == "message" and "subtype" not in event:
            user = event.get("user")
            text = event.get("text")
            channel = event.get("channel")
            print(f"📥 Message from {user} in {channel}: {text}")

            # 👉 You can now pass `text` into your AI bot
            # response = await chat_route({"message": text}, db)

    return {"ok": True}
