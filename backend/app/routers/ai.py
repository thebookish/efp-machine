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
    "Extract the message text (everything after 'send' and before 'to'), "
    "and detect recipients (Slack channels/users or WhatsApp contacts) after 'to'. "
    # "Never guess phone numbers: if unsure, just return the name string. "
    "For general queries, counts, or summaries about orders or Bloomberg messages "
    "(like 'how many orders', 'show me messages from Slack', 'any approved messages'), "
    "always call the natural_query_insight tool. "
    "Otherwise respond with the normal trade/order tools "
    "(update_price, trade, blotter_add, blotter_remove, get_bbo, "
    "order_list, order_create, order_edit, order_delete, order_summary). "
    "Never guess or assume missing values. "
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
    "name": "daily_report_summary",
    "description": "Summarize today's or yesterday's orders and spreads in natural language",
    "parameters": {
      "type": "object",
      "properties": {},
    },
  },
},

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

            elif name == "daily_report_summary":

                tz = timezone.utc
                today = datetime.now(tz)
                start = today - timedelta(days=1)
                end = today

                stmt = (
                    select(
                        func.count(Order.orderId),
                        func.avg(Order.price),
                        func.min(Order.price),
                        func.max(Order.price),
                        func.avg(Order.basis),
                    )
                    .where(and_(Order.createdAt >= start, Order.createdAt < end))
                )
                count_, avg_px, min_px, max_px, avg_basis = (await db.execute(stmt)).one()

                # per contract summary
                per_contract_stmt = (
                    select(Order.contractId, func.count(Order.orderId), func.avg(Order.price))
                    .where(and_(Order.createdAt >= start, Order.createdAt < end))
                    .group_by(Order.contractId)
                )
                per_contract = (await db.execute(per_contract_stmt)).all()

                summary_lines = [
                    f"🗓️ **Order Summary**",
                    f"- Total orders: {count_}",
                    f"- Avg price: {round(avg_px or 0, 2)}",
                    f"- Price range: {round(min_px or 0, 2)} – {round(max_px or 0, 2)}",
                    f"- Avg basis: {round(avg_basis or 0, 2)}",
                    "",
                    "📊 **Per Contract:**",
                ]
                for c, cnt, avgp in per_contract:
                    summary_lines.append(f"• {c}: {cnt} orders, avg price {round(avgp or 0, 2)}")

                result = {"reply": "\n".join(summary_lines)}

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

                # --- Detect question intent ---
                wants_list = any(k in question for k in ["show", "list", "display", "see", "give me", "messages from"])
                wants_yesno = any(k in question for k in ["do we have", "is there", "any message"])
                asks_top_source = "which" in question and "source" in question and "most" in question

                # --- Detect source (Slack, WhatsApp, Bloomberg) ---
                source_filter = None
                if "slack" in question:
                    source_filter = "slack"
                elif "whatsapp" in question:
                    source_filter = "whatsapp"
                elif "bloomberg" in question:
                    source_filter = "bloomberg"

                # --- Time filter detection ---
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

                # --- Base metrics ---
                total_orders = await db.scalar(select(func.count(Order.orderId)))
                total_msgs = await db.scalar(select(func.count(BloombergMessage.eventId)))
                approved_msgs = await db.scalar(
                    select(func.count(BloombergMessage.eventId)).where(BloombergMessage.messageStatus == "approved")
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

                source_counts = {
                    "slack": slack_msgs or 0,
                    "whatsapp": whatsapp_msgs or 0,
                    "bloomberg": bloomberg_msgs or 0,
                }

                # --- 1️⃣ Which source has most messages ---
                if asks_top_source:
                    if total_msgs == 0:
                        result = {"reply": "No messages available from any source yet."}
                    else:
                        top_source = max(source_counts, key=source_counts.get)
                        result = {"reply": f"{top_source.title()} has the most messages with {source_counts[top_source]} entries."}

                # --- 2️⃣ Yes/No style queries (do we have any messages from X?) ---
                elif wants_yesno and source_filter:
                    count_stmt = select(func.count(BloombergMessage.eventId)).where(BloombergMessage.source == source_filter)
                    if start_time:
                        count_stmt = count_stmt.where(
                            and_(BloombergMessage.created_at >= start_time, BloombergMessage.created_at < end_time)
                        )
                    count = await db.scalar(count_stmt) or 0

                    if count > 0:
                        result = {"reply": f"Yes — there are {count} message(s) from {source_filter.title()}."}
                    else:
                        result = {"reply": f"No — no messages from {source_filter.title()} in that time range."}

                # --- 3️⃣ Listing messages (show/list/display) ---
                elif wants_list or "messages from" in question:
                    stmt = select(BloombergMessage).order_by(BloombergMessage.created_at.desc()).limit(10)

                    if source_filter:
                        stmt = stmt.where(BloombergMessage.source == source_filter)
                    if "approved" in question:
                        stmt = stmt.where(BloombergMessage.messageStatus == "approved")
                    elif "drafted" in question:
                        stmt = stmt.where(BloombergMessage.messageStatus == "drafted")

                    if start_time:
                        stmt = stmt.where(and_(BloombergMessage.created_at >= start_time, BloombergMessage.created_at < end_time))

                    rows = await db.execute(stmt)
                    msgs = rows.scalars().all()

                    if not msgs:
                        time_phrase = ""
                        if "today" in question:
                            time_phrase = " today"
                        elif "yesterday" in question:
                            time_phrase = " yesterday"
                        elif "week" in question:
                            time_phrase = " this week"
                        result = {"reply": f"No {source_filter or ''} messages found{time_phrase}."}
                    else:
                        formatted = "\n".join(
                            [f"- [{m.source}] {m.trader_alias or m.trader_uuid}: {m.originalMessage}"
                            for m in msgs]
                        )
                        time_phrase = ""
                        if "today" in question:
                            time_phrase = " from today"
                        elif "yesterday" in question:
                            time_phrase = " from yesterday"
                        elif "week" in question:
                            time_phrase = " from this week"

                        result = {"reply": f"Here are the latest {source_filter or 'recent'} messages{time_phrase}:\n{formatted}"}

                # --- 4️⃣ Default numeric summary ---
                else:
                    summary = (
                        f"📊 Snapshot Summary:\n"
                        f"- Total Orders: {total_orders}\n"
                        f"- Total Messages: {total_msgs}\n"
                        f"- Approved Messages: {approved_msgs}\n"
                        f"- Slack: {slack_msgs}, WhatsApp: {whatsapp_msgs}, Bloomberg: {bloomberg_msgs}"
                    )
                    result = {"reply": summary}

                # --- Polishing pass with GPT for natural tone ---
                try:
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "Rephrase this technical answer into a brief, natural reply in the tone of a professional trading assistant."},
                            {"role": "user", "content": result["reply"]},
                        ],
                    )
                    result["reply"] = completion.choices[0].message.content.strip()
                except Exception:
                    pass


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
