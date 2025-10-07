from twilio.rest import Client
from app.config import settings

# Twilio client
twilio_client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
TWILIO_WHATSAPP_NUMBER='+14155238886' 
async def send_whatsapp_message(numbers: list[str], text: str) -> dict:
    """
    Send a WhatsApp message (with line breaks preserved) to multiple phone numbers.
    """
    # Ensure it's always a list
    if isinstance(numbers, str):
        numbers = [numbers]

    results = []
    for n in numbers:
        try:
            formatted_text = text.replace("\n", "\n")  # WhatsApp supports raw '\n'
            msg = twilio_client.messages.create(
                from_="whatsapp:" + TWILIO_WHATSAPP_NUMBER.strip(),
                to="whatsapp:" + n.strip(),
                body=formatted_text,
            )
            results.append({"target": n, "ok": True, "sid": msg.sid})
        except Exception as e:
            results.append({"target": n, "ok": False, "error": str(e)})
    return results


# async def send_whatsapp_message(to: str, text: str) -> dict:
#     """
#     Send a WhatsApp message using Twilio.
#     :param to: Recipient phone number in E.164 format (+1234567890).
#     :param text: Message content.
#     """
#     try:
#         message = twilio_client.messages.create(
#             from_='whatsapp:+14155238886',
#             body=text,
#             to=f'whatsapp:{to}'
#         )
#         return {"ok": True, "sid": message.sid}
#     except Exception as e:
#         return {"ok": False, "error": str(e)}
