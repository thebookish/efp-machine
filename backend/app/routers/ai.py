from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas import TradeRequest, UpdatePriceRequest, BlotterTradeBase, BlotterRemoveRequest
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade as blotter_add, remove_trade as blotter_remove
from app.services.market import get_quote
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
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC"
}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "You may only respond with tool calls (update_price, trade, get_quote, blotter_add, blotter_remove). "
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

            # ✅ Restrict indices
            idx = args.get("index") or args.get("index_name") or args.get("symbol")
            if idx and idx.upper() not in ALLOWED_INDICES and name != "get_quote":
                return {
                    "reply": f"Sorry, I can only handle approved indices: {', '.join(sorted(ALLOWED_INDICES))}.",
                    "session_id": session_id,
                }

            if name == "update_price":
                if args.get("bid") is None and args.get("offer") is None:
                    return {"reply": f"Please specify at least a bid or offer for {args.get('index','the index')}."}
                if args.get("cash_ref") is None:
                    return {"reply": f"Please provide the cash reference level for {args.get('index','the index')}."}
                return await update_price(UpdatePriceRequest(**args), db)

            elif name == "trade":
                if not all(k in args for k in ("index", "price", "lots", "cash_ref")):
                    return {"reply": f"Please provide full trade details (index, price, lots, cash_ref)."}
                return await trade(TradeRequest(**args), db)

            elif name == "get_quote":
                result = await get_quote(**args)
                if "error" in result:
                    return {"reply": f"Could not fetch data for {result['symbol']}."}
                return {
                    "reply": f"{result['symbol']} (mapped {result['mapped_symbol']}) – Last Price {result['last_price']} {result.get('currency','')}",
                    "session_id": session_id,
                }

            elif name == "blotter_add":
                if not all(k in args for k in ("side", "index_name", "qty", "price")):
                    return {"reply": "Please provide side, index_name, qty, and price for blotter trades."}
                return await blotter_add(BlotterTradeBase(**args), db)

            elif name == "blotter_remove":
                if not args.get("trade_id"):
                    return {"reply": "Please provide the trade_id to remove."}
                return await blotter_remove(BlotterRemoveRequest(**args), db)

            else:
                return {"reply": f"Unknown tool call: {name}", "session_id": session_id}

        # --- 4. Fallback: plain text reply ---
        return {"reply": choice.message.content, "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
