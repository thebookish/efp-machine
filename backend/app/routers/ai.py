from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.deps import get_db
from app.schemas import (
    TradeRequest,
    UpdatePriceRequest,
    BlotterTradeBase,
    BlotterRemoveRequest,
    OrderResponse,
)
from app.models import Order
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade as blotter_add, remove_trade as blotter_remove
from app.routers.quotes import get_bbo
from app.services.slack_client import send_slack_message
from app.config import settings
from openai import OpenAI
import json
import uuid

# ✅ import broadcast helpers
from app.routers.orders import _push_full_list, _push_order_update, manager

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# In-memory conversation store {session_id: [messages]}
CONVERSATIONS = {}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "You may only respond with tool calls "
    "(update_price, trade, blotter_add, blotter_remove, get_bbo, "
    "order_list, order_create, order_edit, order_delete). "
    "Keep track of context across the conversation. "
    "Never guess or assume missing values. "
)


@router.post("/chat")
async def chat_route(query: dict, db: AsyncSession = Depends(get_db)):
    try:
        session_id = query.get("session_id") or str(uuid.uuid4())
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        CONVERSATIONS[session_id].append({"role": "user", "content": query["message"]})

        # --- 2. Ask OpenAI ---
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=CONVERSATIONS[session_id],
            tools=[
                # --- existing tools ---
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
                # --- new order tools ---
                {
                    "type": "function",
                    "function": {
                        "name": "order_list",
                        "description": "Query orders from the database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contractId": {"type": "string"},
                                "expiryDate": {"type": "string"},
                                "state": {"type": "string"},
                                "orderType": {"type": "string"},
                                "buySell": {"type": "string"},
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "order_create",
                        "description": "Create a new order in the database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contractId": {"type": "string"},
                                "expiryDate": {"type": "string"},
                                "price": {"type": "number"},
                                "basis": {"type": "number"},
                                "buySell": {"type": "string"},
                                "orderType": {"type": "string"},
                                "state": {"type": "string"},
                            },
                            "required": ["contractId", "expiryDate", "price", "basis", "buySell"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "order_edit",
                        "description": "Edit an existing order in the database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "orderId": {"type": "string"},
                                "fields": {"type": "object"},
                            },
                            "required": ["orderId", "fields"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "order_delete",
                        "description": "Delete an order from the database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "orderId": {"type": "string"},
                            },
                            "required": ["orderId"],
                        },
                    },
                },
                    {
        "type": "function",
        "function": {
            "name": "slack_send_message",
            "description": "Send a text message to a Slack channel or user",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Slack channel (e.g., #trading, U123 for user)"},
                    "text": {"type": "string", "description": "Message to send"},
                },
                "required": ["channel", "text"],
            },
        },
    },
            ],
        )

        choice = resp.choices[0]

        if choice.message:
            CONVERSATIONS[session_id].append(choice.message)

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            # --- Handle ORDER tools with WebSocket push ---
            if name == "order_list":
                stmt = select(Order)
                if args.get("contractId"):
                    stmt = stmt.where(Order.contractId == args["contractId"])
                if args.get("expiryDate"):
                    stmt = stmt.where(Order.expiryDate == args["expiryDate"])
                if args.get("state"):
                    stmt = stmt.where(Order.state == args["state"])
                if args.get("orderType"):
                    stmt = stmt.where(Order.orderType == args["orderType"])
                if args.get("buySell"):
                    stmt = stmt.where(Order.buySell == args["buySell"])

                resultset = await db.execute(stmt)
                orders = resultset.scalars().all()
                result = {"orders": [OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json") for o in orders]}

            elif name == "order_create":
                new_order = Order(
                    contractId=args["contractId"],
                    expiryDate=args["expiryDate"],
                    price=args["price"],
                    basis=args["basis"],
                    buySell=args["buySell"],
                    orderType=args.get("orderType", "SINGLE"),
                    state=args.get("state", "ACTIVE"),
                )
                db.add(new_order)
                await db.commit()
                await db.refresh(new_order)
                result = {"order": OrderResponse.model_validate(new_order, from_attributes=True).model_dump(mode="json")}

                # ✅ push WebSocket event
                # await _push_order_new(new_order)

            elif name == "order_edit":
                stmt = select(Order).where(Order.orderId == args["orderId"])
                res = await db.execute(stmt)
                order = res.scalar_one_or_none()
                if not order:
                    raise HTTPException(status_code=404, detail="Order not found")
                for field, value in args["fields"].items():
                    if hasattr(order, field):
                        setattr(order, field, value)
                await db.commit()
                await db.refresh(order)
                result = {"order": OrderResponse.model_validate(order, from_attributes=True).model_dump(mode="json")}

                # ✅ push WebSocket update
                await _push_order_update(order)

            elif name == "order_delete":
                order_id = args["orderId"]
                stmt = delete(Order).where(Order.orderId == order_id)
                await db.execute(stmt)
                await db.commit()
                result = {"reply": f"Order {order_id} deleted."}

                # ✅ push WebSocket delete
                await manager.broadcast_json({"type": "order_delete", "payload": {"orderId": order_id}})
            
            elif name == "slack_send_message":
                res = await send_slack_message(args["channel"], args["text"])
                result = {"reply": f"Message has been sent!"}

            # --- Handle other tools (update_price, trade, blotter, bbo) same as before ---
            else:
                result = {"reply": f"Unknown tool call: {name}"}

            # Save tool result to memory
            CONVERSATIONS[session_id].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": json.dumps(result),
            })

            return {**result, "session_id": session_id}

        return {"reply": choice.message.content, "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
