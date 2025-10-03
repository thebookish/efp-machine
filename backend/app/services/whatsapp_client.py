from twilio.rest import Client
from app.config import settings

# Twilio client
twilio_client = Client('ACeb0700777fee4f0e60de0e7cb0bc40fd','ac6089c725cbe5fcd81565af056bf7a5')
TWILIO_WHATSAPP_NUMBER='+14155238886' 
async def send_whatsapp_message(numbers: list[str], text: str) -> dict:
    """
    Send a WhatsApp message to multiple phone numbers.
    numbers: list of phone numbers in E.164 (+123...).
    """
    results = []
    for n in numbers:
        try:
            msg = twilio_client.messages.create(
                from_="whatsapp:" + settings.TWILIO_WHATSAPP_NUMBER.strip(),
                to="whatsapp:" + n.strip(),
                body=text,
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
