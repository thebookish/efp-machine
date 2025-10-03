from app.services.whatsapp_client import send_whatsapp_message
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.deps import get_db
from app.schemas import OrderResponse
from app.models import Order
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade as blotter_add, remove_trade as blotter_remove
from app.routers.quotes import get_bbo
from app.services.slack_client import send_slack_message
from app.routers.orders import _push_order_update, manager
from app.config import settings
from openai import OpenAI
import json, uuid

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

CONVERSATIONS = {}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "If the user message starts with 'send', always call the broadcast_message tool. "
    "Extract the message text (everything after 'send' and before 'to'), "
    "and detect recipients (Slack channels/users or WhatsApp contacts) after 'to'. "
    "Never guess phone numbers: if unsure, just return the name string. "
    "Otherwise respond with the normal trade/order tools "
    "(update_price, trade, blotter_add, blotter_remove, get_bbo, "
    "order_list, order_create, order_edit, order_delete, order_summary). "
    "Never guess or assume missing values. "
)


# --- Build order context for RAG ---
async def build_order_context(db: AsyncSession, limit: int = 50) -> str:
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        return "No orders found in the database."

    context_lines = []
    for o in orders:
        context_lines.append(
            f"Order {o.orderId}: {o.contractId} {o.expiryDate} "
            f"{o.buySell} {o.price} vs {o.basis}, "
            f"type={o.orderType}, state={o.state}"
        )
    return "\n".join(context_lines)


@router.post("/chat")
async def chat_route(query: dict, db: AsyncSession = Depends(get_db)):
    try:
        session_id = query.get("session_id") or str(uuid.uuid4())
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        CONVERSATIONS[session_id].append({"role": "user", "content": query["message"]})

        # --- Call OpenAI ---
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=CONVERSATIONS[session_id],
            tools=[
                # Existing tools
                {
                    "type": "function",
                    "function": {
                        "name": "order_list",
                        "description": "Query orders with filters",
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
                        "name": "order_summary",
                        "description": "Summarize orders (counts, best prices, avg, etc.)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contractId": {"type": "string"},
                                "expiryDate": {"type": "string"},
                                "state": {"type": "string"},
                            },
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "order_create",
                        "description": "Create a new order",
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
                        "description": "Edit an existing order",
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
                        "description": "Delete an order",
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
                        "description": "Send a Slack message to channel or user",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "channel": {"type": "string"},
                                "text": {"type": "string"},
                            },
                            "required": ["channel", "text"],
                        },
                    },
                },
                {
    "type": "function",
    "function": {
        "name": "whatsapp_send_message",
        "description": "Recognize 'send ... to ...' style instructions and split into message text and whatsapp numbers and send message to whatsapp",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Phone number in +E.164 format"},
                "text": {"type": "string", "description": "Message to send"},
            },
            "required": ["to", "text"],
        },
    },
    
},

{
  "type": "function",
  "function": {
    "name": "broadcast_message",
    "description": "Send a message to Slack and/or WhatsApp. Auto-detect text vs recipients from natural language input.",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "description": "Message text to send"},
        "slack_targets": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Slack channels (#trading) or user IDs"
        },
        "whatsapp_numbers": {
          "type": "array",
          "items": {"type": "string"},
          "description": "WhatsApp numbers or contact names"
        }
      },
      "required": ["text"]
    }
  }
}


            ],
        )

        choice = resp.choices[0]
        if choice.message:
            CONVERSATIONS[session_id].append(choice.message)

        # --- Tool calls ---
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

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

                rows = await db.execute(stmt)
                orders = rows.scalars().all()
                result = {"orders": [OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json") for o in orders]}

            elif name == "order_summary":
                stmt = select(
                    func.count(Order.orderId),
                    func.max(Order.price),
                    func.min(Order.price),
                    func.avg(Order.price),
                )
                if args.get("contractId"):
                    stmt = stmt.where(Order.contractId == args["contractId"])
                if args.get("expiryDate"):
                    stmt = stmt.where(Order.expiryDate == args["expiryDate"])
                if args.get("state"):
                    stmt = stmt.where(Order.state == args["state"])

                row = (await db.execute(stmt)).one()
                result = {
                    "total_orders": row[0],
                    "max_price": row[1],
                    "min_price": row[2],
                    "avg_price": float(row[3]) if row[3] else None,
                }

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
                await _push_order_update(new_order)

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
                await _push_order_update(order)

            elif name == "order_delete":
                order_id = args["orderId"]
                stmt = delete(Order).where(Order.orderId == order_id)
                await db.execute(stmt)
                await db.commit()
                result = {"reply": f"Order {order_id} deleted."}
                await manager.broadcast_json({"type": "order_delete", "payload": {"orderId": order_id}})

            elif name == "slack_send_message":
                await send_slack_message(args["channel"], args["text"])
                result = {"reply": f"Message sent to {args['channel']}"}

            elif name == "whatsapp_send_message":
                res = await send_whatsapp_message(args["to"], args["text"])
                if not res["ok"]:
                    result = {"reply": f"Failed to send WhatsApp: {res['error']}"}
                else:
                    result = {"reply": f"WhatsApp message sent to {args['to']}"}

            elif name == "broadcast_message":
                message_text = args["text"]
                whatsapp_numbers = args.get("whatsapp_numbers", [])
                if isinstance(whatsapp_numbers, str):
                    whatsapp_numbers = [whatsapp_numbers]

                slack_targets = args.get("slack_targets", [])
                if isinstance(slack_targets, str):
                    slack_targets = [slack_targets]

                results = {"slack": [], "whatsapp": []} 

                if slack_targets:
                    res = await send_slack_message(slack_targets, message_text)
                    results["slack"].extend(res)

                if whatsapp_numbers:
                    res = await send_whatsapp_message(whatsapp_numbers, message_text)
                    results["whatsapp"].extend(res)

                result = {"reply": "Broadcast completed", "results": results}

            else:
                result = {"reply": f"Unknown tool call: {name}"}

            CONVERSATIONS[session_id].append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": name,
                "content": json.dumps(result),
            })
            return {**result, "session_id": session_id}

        # --- Natural language fallback with DB context ---
        context = await build_order_context(db)
        rag_prompt = f"""
        You are the trading assistant. 
        Here are the latest known orders:

        {context}

        User question: {query["message"]}
        Answer using the orders above. If nothing matches, say 'No relevant orders found'.
        """
        rag_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": rag_prompt}],
        )
        return {"reply": rag_resp.choices[0].message.content, "session_id": session_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
