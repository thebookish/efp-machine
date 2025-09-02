# backend/app/routers/ai.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas import TradeRequest, UpdatePriceRequest
from app.routers.efp import update_price, trade
from app.config import settings
from openai import OpenAI
import json

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "Always decide between calling update_price or trade. "
    "Do not output free text."
)

@router.post("/chat")
async def chat_route(query: dict, db: AsyncSession = Depends(get_db)):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query["message"]},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "update_price",
                        "description": "Update bid/offer for an index",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "string"},
                                "bid": {"type": "number"},
                                "offer": {"type": "number"},
                                "cash_ref": {"type": "number"},
                                "dean_confirm": {"type": "boolean"},
                            },
                            "required": ["index", "cash_ref"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "trade",
                        "description": "Log a trade recap and remove the line",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "string"},
                                "price": {"type": "number"},
                                "lots": {"type": "integer"},
                                "cash_ref": {"type": "number"},
                            },
                            "required": ["index", "price", "lots", "cash_ref"],
                        },
                    },
                },
            ],
        )

        choice = resp.choices[0]

        # ✅ correct: tool calls are on choice.message
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if name == "update_price":
                return await update_price(UpdatePriceRequest(**args), db)
            elif name == "trade":
                return await trade(TradeRequest(**args), db)
            else:
                return {"reply": f"Unknown tool call: {name}"}

        # fallback if model gives text
        return {"reply": choice.message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
