# from http import client
from fastapi import APIRouter, HTTPException
from app.services.slack_client import list_slack_channels, list_slack_users, send_slack_message,client
from app.schemas import SlackMessageRequest, SlackMessageResponse

router = APIRouter(prefix="/api/slack", tags=["slack"])

@router.post("/send", response_model=SlackMessageResponse)
async def send_message(payload: SlackMessageRequest):
    """
    Send a message to Slack from frontend.
    """
    result = await send_slack_message(payload.channel, payload.text)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/channels")
async def get_channels():
    result = await list_slack_channels()
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["channels"]

@router.get("/users")
async def get_users():
    result = await list_slack_users()
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result["users"]

@router.get("/destinations")
async def get_slack_destinations():
    try:
        channels = client.conversations_list(types="public_channel,private_channel").get("channels", [])
        users = client.users_list().get("members", [])

        results = []

        # Channels
        for c in channels:
            if not c.get("is_archived"):
                results.append({
                    "id": c["id"],
                    "name": f"#{c['name']}",
                    "type": "channel",
                })

        # Users
        for u in users:
            if not u.get("deleted") and not u.get("is_bot"):
                results.append({
                    "id": u["id"],
                    "name": u["profile"].get("real_name") or u["name"],
                    "type": "user",
                })

        return {"destinations": results}
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Slack API error: {e.response['error']}")