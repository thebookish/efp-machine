from app.services.market import get_quote
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db
from app.schemas import TradeRequest, UpdatePriceRequest
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade, remove_trade  # ✅ import blotter handlers
from app.config import settings
from openai import OpenAI
import json

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

ALLOWED_INDICES = {
    "SX5E", "FTSE", "DAX", "SMI", "MIB",
    "CAC", "IBEX", "AEX", "OMX", "SX7E", "SX7E CC"
}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "You may only respond with valid tool calls (update_price, trade, get_quote, blotter_add, blotter_remove). "
    "Never guess or assume missing values. "
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
                {
                    "type": "function",
                    "function": {
                        "name": "get_quote",
                        "description": "Fetch last price from Yahoo Finance",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "symbol": {"type": "string", "description": "Ticker symbol, e.g., ^STOXX50E"},
                            },
                            "required": ["symbol"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "blotter_add",
                        "description": "Add or update a blotter trade",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "side": {"type": "string", "enum": ["BUY", "SELL"]},
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

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            # ✅ Enforce allowed indices
            idx = args.get("index") or args.get("index_name") or args.get("symbol")
            if idx and idx.upper() not in ALLOWED_INDICES:
                return {"reply": f"Sorry, I only handle approved indices: {', '.join(sorted(ALLOWED_INDICES))}."}

            if name == "update_price":
                if args.get("bid") is None and args.get("offer") is None:
                    return {"reply": f"Please specify at least a bid or offer for {args.get('index','the index')}."}
                if args.get("cash_ref") is None:
                    return {"reply": f"Please provide the cash reference level for {args.get('index','the index')}."}
                return await update_price(UpdatePriceRequest(**args), db)

            elif name == "trade":
                if args.get("price") is None or args.get("lots") is None or args.get("cash_ref") is None:
                    return {"reply": f"Please provide full trade details: price, lots, and cash_ref for {args.get('index','the index')}."}
                return await trade(TradeRequest(**args), db)

            elif name == "get_quote":
                if not args.get("symbol"):
                    return {"reply": "Please provide a valid symbol (e.g., SX5E, DAX, FTSE)."}
                result = await get_quote(**args)
                if "error" in result:
                    return {"reply": f"Could not find data for {result['symbol']}."}
                return {"reply": f"{result['symbol']} – Last Price: {result['last_price']} {result.get('currency','')}"}

            elif name == "blotter_add":
                return await add_trade(args, db)

            elif name == "blotter_remove":
                return await remove_trade(args, db)

            else:
                return {"reply": f"Unknown tool call: {name}"}

        return {"reply": choice.message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
