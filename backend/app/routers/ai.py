# backend/app/routers/ai.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas import (
    TradeRequest,
    UpdatePriceRequest,
    BlotterTradeBase,
    BlotterRemoveRequest,
)
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade as blotter_add, remove_trade as blotter_remove
from app.services.market import get_quote
from app.routers.quotes import get_bbo
from app.config import settings
from openai import OpenAI
import json
import uuid

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# In-memory conversation store {session_id: [messages]}
CONVERSATIONS = {}

ALLOWED_INDICES = {
    "SX5E", "FTSE", "DAX", "SMI", "MIB",
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC",
}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "You may only respond with tool calls (update_price, trade, get_quote, blotter_add, blotter_remove, get_bbo). "
    "Keep track of context across the conversation. "
    "Never guess or assume missing values. "
)


@router.post("/chat")
async def chat_route(query: dict, db: AsyncSession = Depends(get_db)):
    try:
        # --- 1. Manage conversation memory ---
        session_id = query.get("session_id") or str(uuid.uuid4())
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        CONVERSATIONS[session_id].append({"role": "user", "content": query["message"]})

        # --- 2. Ask OpenAI ---
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=CONVERSATIONS[session_id],
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
                {
                    "type": "function",
                    "function": {
                        "name": "get_quote",
                        "description": "Fetch last price from Yahoo Finance",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string"},
                            },
                            "required": ["symbol"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "blotter_add",
                        "description": "Add or update a trade in blotter",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "side": {"type": "string"},
                                "index_name": {"type": "string"},
                                "qty": {"type": "integer"},
                                "price": {"type": "number"},
                            },
                            "required": ["side", "index_name", "qty", "price"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "blotter_remove",
                        "description": "Remove a trade from blotter",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "trade_id": {"type": "integer"},
                            },
                            "required": ["trade_id"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_bbo",
                        "description": "Get the best bid/offer for an index from client quotes",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "string"},
                            },
                            "required": ["index"],
                        },
                    },
                },
            ],
        )

        choice = resp.choices[0]

        # Save AI reply in conversation
        if choice.message:
            CONVERSATIONS[session_id].append(choice.message)

        # --- 3. Handle tool calls ---
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            # --- Handle each tool ---
            if name == "update_price":
                if "confirm" in query["message"].lower():
                    args["dean_confirm"] = True
                res = await update_price(UpdatePriceRequest(**args), db)
                result = res.dict() if hasattr(res, "dict") else dict(res)

            elif name == "trade":
                res = await trade(TradeRequest(**args), db)
                result = res.dict() if hasattr(res, "dict") else dict(res)

            elif name == "get_quote":
                res = await get_quote(**args)
                if "error" in res:
                    result = {"reply": f"Could not fetch data for {res['symbol']}."}
                else:
                    result = {
                        "reply": f"{res['symbol']} (mapped {res['mapped_symbol']}) – "
                                 f"Last Price {res['last_price']} {res.get('currency','')}"
                    }

            elif name == "blotter_add":
                res = await blotter_add(BlotterTradeBase(**args), db)
                if hasattr(res, "dict"):
                    res = res.dict()
                reply = (
                    f"Added/updated blotter trade: {res['side']} {res['qty']} {res['index_name']} "
                    f"at avg price {res['avg_price']}."
                )
                result = {"reply": reply}

            elif name == "blotter_remove":
                res = await blotter_remove(BlotterRemoveRequest(**args), db)
                if hasattr(res, "dict"):
                    res = res.dict()
                reply = f"Trade removed from blotter. {res.get('detail','')}"
                result = {"reply": reply}

            elif name == "get_bbo":
                res = await get_bbo(args["index"])
                if "detail" in res:
                    result = {"reply": res["detail"]}
                else:
                    result = {
                        "reply": f"Best bid for {res['index']} is {res['best_bid']}, "
                                 f"best offer is {res['best_offer']}."
                    }

            else:
                result = {"reply": f"Unknown tool call: {name}"}

            # ✅ Append tool result into conversation
            CONVERSATIONS[session_id].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": json.dumps(result),
            })

            return {**result, "session_id": session_id}

        # --- 4. Fallback: plain text reply ---
        return {"reply": choice.message.content, "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
