from app.services.whatsapp_client import send_whatsapp_message
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.deps import get_db
from app.schemas import OrderResponse
from app.models import BloombergMessage, Order
from app.routers.efp import update_price, trade
from app.routers.blotter import add_trade as blotter_add, remove_trade as blotter_remove
from app.routers.quotes import get_bbo
from app.services.slack_client import send_slack_message
from app.routers.orders import _push_order_update, manager
from app.config import settings
from openai import OpenAI
import json, uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, func

router = APIRouter(prefix="/api/ai", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

CONVERSATIONS = {}

SYSTEM_PROMPT = (
    "You are the EFP Machine assistant. "
    "If the user message starts with 'send', always call the broadcast_message tool. "
"Extract the message text (everything after 'send' and before 'to'), even across multiple lines. "
"Detect recipients strictly as follows: "
"- If the recipient starts with '#' or matches a Slack channel ID pattern (like 'CXXXX'), it is a Slack target. "
"- If it looks like a name or number, it is a WhatsApp contact. "
"Never leave both recipient lists empty — if unsure, default to Slack when the name starts with '#'. "
    # "Never guess phone numbers: if unsure, just return the name string. "
    "For general queries, counts, or summaries about orders or Bloomberg messages "
    "(like 'how many orders', 'show me messages from Slack', 'any approved messages'), "
    "always call the natural_query_insight tool. "
    "Otherwise respond with the normal trade/order tools "
    "( order_list, order_create, order_edit, order_delete, order_summary,predict_order_suggestion). "
    "Never guess or assume missing values. "
"Always answer directly from available database records. "
"Never provide summaries, estimates, or narrative explanations unless explicitly asked (e.g., 'summarize' or 'overview'). "
"If no records match, respond clearly: 'No matching records found.' "
"Do not rephrase or elaborate beyond the user’s exact request."

)


# --- Build order context for RAG ---
async def build_order_context(db: AsyncSession, limit: int = 50) -> str:
    stmt = select(Order).order_by(Order.createdAt.desc()).limit(limit)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        return "No orders found in the database."

    context_lines = []
    for o in orders:
        context_lines.append(
            f"Order {o.orderId}: {o.contractId} {o.expiryDate} "
            f"{o.side} {o.price} vs {o.basis}, "
            f"state={o.orderStatus}"
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
},
{
  "type": "function",
  "function": {
    "name": "predict_order_suggestion",
    "description": "Analyze historical orders to suggest a good target price or basis for a given contract/expiry",
    "parameters": {
      "type": "object",
      "properties": {
        "contractId": {"type": "string"},
        "expiryDate": {"type": "string"}
      },
      "required": ["contractId", "expiryDate"]
    }
  }
}
,

{
  "type": "function",
  "function": {
    "name": "natural_query_insight",
    "description": "Answer natural language questions about orders or Bloomberg messages — e.g., count, sources, statuses, active/target orders, etc.",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {"type": "string", "description": "The user's original question or query"}
      },
      "required": ["question"]
    }
  }
},

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
                    stmt = stmt.where(Order.orderStatus == args["orderStatus"])
        
                if args.get("buySell"):
                    stmt = stmt.where(Order.side == args["side"])

                rows = await db.execute(stmt)
                orders = rows.scalars().all()
                result = {"orders": [OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json") for o in orders]}


            elif name == "order_create":
                new_order = Order(
                    contractId=args["contractId"],
                    expiryDate=args["expiryDate"],
                    price=args["price"],
                    basis=args["basis"],
                    buySell=args["buySell"],
                    orderType=args.get("orderType", "SINGLE"),
                    # state=args.get("state", "ACTIVE"),
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

            elif name == "broadcast_message":
                message_text = args["text"]
                whatsapp_numbers = args.get("whatsapp_numbers", [])
                slack_targets = args.get("slack_targets", [])

                # --- Normalize types ---
                if isinstance(whatsapp_numbers, str):
                    whatsapp_numbers = [whatsapp_numbers]
                if isinstance(slack_targets, str):
                    slack_targets = [slack_targets]

                # --- Auto-separate by prefix ---
                # Slack channels usually start with '#', WhatsApp targets are phone numbers or names
                slack_targets = [t for t in slack_targets if t.startswith("#") or t.startswith("C") or t.startswith("U")]
                whatsapp_numbers = [w for w in whatsapp_numbers if not (w.startswith("#") or w.startswith("C") or w.startswith("U"))]

                results = {"slack": [], "whatsapp": []}

                # --- Dispatch to Slack ---
                if slack_targets:
                    try:
                        slack_res = await send_slack_message(slack_targets, message_text)
                        results["slack"].extend(slack_res)
                    except Exception as e:
                        results["slack"].append({"ok": False, "error": str(e)})

                # --- Dispatch to WhatsApp ---
                if whatsapp_numbers:
                    try:
                        wp_res = await send_whatsapp_message(whatsapp_numbers, message_text)
                        results["whatsapp"].extend(wp_res)
                    except Exception as e:
                        results["whatsapp"].append({"ok": False, "error": str(e)})

                result = {"reply": f"Message sent!", "results": results}


            elif name == "predict_order_suggestion":
                contract = args["contractId"]
                expiry = args["expiryDate"]
                expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()

                stmt = select(Order.price, Order.basis).where(Order.contractId == contract, Order.expiryDate ==  expiry_date)
                rows = await db.execute(stmt)
                data = rows.fetchall()

                if not data:
                    result = {"reply": f"No past orders found for {contract} {expiry}."}
                else:
                    prices = [r[0] for r in data if r[0] is not None]
                    avg_price = sum(prices) / len(prices)
                    min_price, max_price = min(prices), max(prices)

                    suggestion = round((avg_price + max_price) / 2, 2)
                    result = {
                        "reply": f"Most traders placed {contract} {expiry} between {min_price:.2f}–{max_price:.2f}. "
                                f"Suggest {suggestion:.2f} based on recent tightening."
                    }

            elif name == "natural_query_insight":
                question = args.get("question", "").lower()

                # --- Detect intent ---
                wants_count = "how many" in question or "count" in question
                wants_list = any(k in question for k in ["show", "list", "display", "see", "messages from", "orders"])
                wants_yesno = any(k in question for k in ["do we have", "is there", "any order", "any message"])
                asks_top_source = "which" in question and ("source" in question or "contract" in question) and "most" in question
                wants_avg = "average" in question or "avg" in question
                wants_high = "highest" in question or "max" in question
                wants_low = "lowest" in question or "min" in question

                # --- Detect entity ---
                is_order_query = "order" in question or "orders" in question
                is_message_query = "message" in question or "messages" in question

                # --- Detect filters ---
                status_filter = None
                if "approved" in question:
                    status_filter = "approved"
                elif "drafted" in question:
                    status_filter = "drafted"
                elif "received" in question:
                    status_filter = "received"
                elif "active" in question:
                    status_filter = "active"
                elif "rejected" in question:
                    status_filter = "rejected"

                side_filter = None
                if "buy" in question:
                    side_filter = "buy"
                elif "sell" in question:
                    side_filter = "sell"

                # --- Source filters (for messages) ---
                source_filter = None
                if "slack" in question:
                    source_filter = "slack"
                elif "whatsapp" in question:
                    source_filter = "whatsapp"
                elif "bloomberg" in question:
                    source_filter = "bloomberg"
                elif "symphony" in question:
                    source_filter = "symphony"

                # --- Contract filter (for orders) ---
                contract_filter = None
                for sym in ["sx5e", "sx7e", "sxpe", "sxee"]:
                    if sym in question:
                        contract_filter = sym.upper()
                        break

                # --- Time filters ---
                tz = timezone.utc
                now = datetime.now(tz)
                start_time = None
                end_time = now
                if "today" in question:
                    start_time = datetime(now.year, now.month, now.day, tzinfo=tz)
                elif "yesterday" in question:
                    start_time = datetime(now.year, now.month, now.day, tzinfo=tz) - timedelta(days=1)
                    end_time = datetime(now.year, now.month, now.day, tzinfo=tz)
                elif "week" in question or "past 7 days" in question:
                    start_time = now - timedelta(days=7)
                elif "last 2 days" in question:
                    start_time = now - timedelta(days=2)

                # =======================
                # --- MESSAGE QUERIES ---
                # =======================
                if is_message_query:
                    total_msgs = await db.scalar(select(func.count(BloombergMessage.eventId)))
                    approved_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.messageStatus == "approved")
                    )
                    drafted_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.messageStatus == "drafted")
                    )
                    received_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.messageStatus == "received")
                    )
                    slack_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == "slack")
                    )
                    whatsapp_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == "whatsapp")
                    )
                    bloomberg_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == "bloomberg")
                    )
                    symphony_msgs = await db.scalar(
                        select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == "symphony")
                    )

                    if wants_count:
                        count_stmt = select(func.count(BloombergMessage.eventId))
                        if status_filter:
                            count_stmt = count_stmt.where(BloombergMessage.messageStatus == status_filter)
                        if source_filter:
                            count_stmt = count_stmt.where(BloombergMessage.source == source_filter)
                        if start_time:
                            count_stmt = count_stmt.where(and_(BloombergMessage.created_at >= start_time, BloombergMessage.created_at < end_time))
                        count = await db.scalar(count_stmt) or 0
                        result = {"reply": f"There are {count} {status_filter or ''} {source_filter or ''} messages.".strip()}

                    elif wants_list:
                        stmt = select(BloombergMessage).order_by(BloombergMessage.created_at.desc()).limit(10)
                        if status_filter:
                            stmt = stmt.where(BloombergMessage.messageStatus == status_filter)
                        if source_filter:
                            stmt = stmt.where(BloombergMessage.source == source_filter)
                        if start_time:
                            stmt = stmt.where(and_(BloombergMessage.created_at >= start_time, BloombergMessage.created_at < end_time))
                        rows = await db.execute(stmt)
                        msgs = rows.scalars().all()
                        if not msgs:
                            result = {"reply": "No matching messages found."}
                        else:
                            formatted = "\n".join(
                                [f"- [{m.source}] {m.trader_alias or m.trader_uuid}: {m.originalMessage}" for m in msgs]
                            )
                            result = {"reply": f"Here are the latest {status_filter or source_filter or 'recent'} messages:\n{formatted}"}

                    elif wants_yesno and source_filter:
                        count_stmt = select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == source_filter)
                        if start_time:
                            count_stmt = count_stmt.where(and_(BloombergMessage.created_at >= start_time, BloombergMessage.created_at < end_time))
                        count = await db.scalar(count_stmt) or 0
                        result = {"reply": f"Yes — {count} message(s) from {source_filter.title()}." if count else f"No — none from {source_filter.title()}."}

                    elif asks_top_source:
                        counts = {
                            "Slack": slack_msgs or 0,
                            "WhatsApp": whatsapp_msgs or 0,
                            "Bloomberg": bloomberg_msgs or 0,
                            "Symphony": symphony_msgs or 0,
                        }
                        top_source = max(counts, key=counts.get) if sum(counts.values()) else None
                        result = {"reply": f"{top_source} has the most messages with {counts[top_source]} entries." if top_source else "No messages found."}

                    else:
                        result = {"reply": f"There are {total_msgs} total messages."}

                # ====================
                # --- ORDER QUERIES ---
                # ====================
                elif is_order_query:
                    total_orders = await db.scalar(select(func.count(Order.orderId)))

                    # --- Count queries ---
                    if wants_count:
                        stmt = select(func.count(Order.orderId))
                        if contract_filter:
                            stmt = stmt.where(Order.contractId.ilike(f"%{contract_filter}%"))
                        if side_filter:
                            stmt = stmt.where(Order.side.ilike(f"%{side_filter}%"))
                        if status_filter:
                            stmt = stmt.where(Order.orderStatus.ilike(f"%{status_filter}%"))
                        if start_time:
                            stmt = stmt.where(and_(Order.createdAt >= start_time, Order.createdAt < end_time))
                        count = await db.scalar(stmt) or 0
                        result = {"reply": f"There are {count} {status_filter or ''} {contract_filter or ''} {side_filter or ''} orders.".strip()}

                    # --- Analytics queries (avg/high/low) ---
                    elif wants_avg or wants_high or wants_low:
                        metric = "price" if "price" in question else "basis"
                        column = getattr(Order, metric)
                        base_stmt = select(
                            func.avg(column) if wants_avg else func.max(column) if wants_high else func.min(column)
                        )
                        if contract_filter:
                            base_stmt = base_stmt.where(Order.contractId.ilike(f"%{contract_filter}%"))
                        if start_time:
                            base_stmt = base_stmt.where(and_(Order.createdAt >= start_time, Order.createdAt < end_time))
                        value = await db.scalar(base_stmt)
                        if value is None:
                            result = {"reply": f"No matching orders found to calculate {metric}."}
                        else:
                            desc = "average" if wants_avg else "highest" if wants_high else "lowest"
                            result = {"reply": f"The {desc} {metric} for {contract_filter or 'all contracts'} is {round(value, 2)}."}

                    # --- Top contract (most orders) ---
                    elif asks_top_source:
                        stmt = select(Order.contractId, func.count(Order.orderId)).group_by(Order.contractId)
                        data = (await db.execute(stmt)).all()
                        if not data:
                            result = {"reply": "No orders found."}
                        else:
                            top = max(data, key=lambda x: x[1])
                            result = {"reply": f"{top[0]} has the most orders with {top[1]} entries."}

                    # --- List queries ---
                    elif wants_list:
                        stmt = select(Order).order_by(Order.createdAt.desc()).limit(10)
                        if contract_filter:
                            stmt = stmt.where(Order.contractId.ilike(f"%{contract_filter}%"))
                        if side_filter:
                            stmt = stmt.where(Order.side.ilike(f"%{side_filter}%"))
                        if start_time:
                            stmt = stmt.where(and_(Order.createdAt >= start_time, Order.createdAt < end_time))
                        rows = await db.execute(stmt)
                        orders = rows.scalars().all()
                        if not orders:
                            result = {"reply": "No matching orders found."}
                        else:
                            formatted = "\n".join(
                                [f"- {o.contractId} {o.expiryDate} {o.side} {o.price}/{o.basis} ({o.orderStatus})" for o in orders]
                            )
                            result = {"reply": f"Here are recent orders:\n{formatted}"}

                    else:
                        result = {"reply": f"There are {total_orders} total orders."}

                # --- Fallback ---
                else:
                    total_orders = await db.scalar(select(func.count(Order.orderId)))
                    total_msgs = await db.scalar(select(func.count(BloombergMessage.eventId)))
                    result = {"reply": f"There are {total_orders} orders and {total_msgs} messages currently in the system."}


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
