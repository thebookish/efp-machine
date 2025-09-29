from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings

client = WebClient(token='xoxb-9589939613474-9586561820389-58IdPAdblm2XbaHFdy0f0w3c')

async def send_slack_message(channel: str, text: str) -> dict:
    """
    Send a message to a Slack channel or user.
    - channel: channel ID (C123...), user ID (U123...), or channel name (#general).
    - text: message string.
    """
    try:
        response = client.chat_postMessage(channel=channel, text=text)
        return {"ok": True, "ts": response["ts"], "channel": response["channel"]}
    except SlackApiError as e:
        return {"ok": False, "error": str(e)}
