from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.config import settings

client = WebClient(token=settings.SLACK)

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

client = AsyncWebClient(token=settings.SLACK)

async def send_slack_message(targets: list[str] | str, text: str) -> dict:
    """
    Send messages (plain, markdown, or code-style multi-line) to Slack using blocks.
    Automatically formats multi-line messages as code blocks for clean alignment.
    """
    if isinstance(targets, str):
        targets = [targets]

    formatted_text = text.strip()

    # Detect if the message spans multiple lines — format as code block
    if "\n" in formatted_text:
        formatted_text = f"```{formatted_text}```"

    results = []

    for t in targets:
        try:
            response = await client.chat_postMessage(
                channel=t.strip(),
                text=text,  # fallback plain text
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": formatted_text
                        }
                    }
                ]
            )

            results.append({
                "target": t,
                "ok": True,
                "ts": response.get("ts"),
                "channel": response.get("channel")
            })

        except SlackApiError as e:
            results.append({
                "target": t,
                "ok": False,
                "error": e.response.get("error", str(e))
            })
        except Exception as e:
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