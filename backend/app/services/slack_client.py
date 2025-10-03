from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings

client = WebClient(token='xoxb-9589939613474-9586561820389-Jv4BTKXZIPYMNTF3jpdsNfrN')

async def send_slack_message(targets: list[str], text: str) -> dict:
    """
    Send a message to multiple Slack channels/users.
    targets: list of channel IDs (C123...) or user IDs (U123...).
    """
    results = []
    for t in targets:
        try:
            response = client.chat_postMessage(channel=t, text=text)
            results.append({"target": t, "ok": True, "ts": response["ts"]})
        except SlackApiError as e:
            results.append({"target": t, "ok": False, "error": str(e)})
    return results
    
async def list_slack_channels() -> dict:
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        channels = [
            {"id": c["id"], "name": c["name"]}
            for c in response["channels"]
        ]
        return {"ok": True, "channels": channels}
    except SlackApiError as e:
        return {"ok": False, "error": str(e.response['error'])}

async def list_slack_users() -> dict:
    try:
        response = client.users_list()
        users = [
            {"id": u["id"], "name": u["name"], "real_name": u.get("real_name")}
            for u in response["members"]
            if not u.get("is_bot") and not u.get("deleted")
        ]
        return {"ok": True, "users": users}
    except SlackApiError as e:
        return {"ok": False, "error": str(e.response['error'])}