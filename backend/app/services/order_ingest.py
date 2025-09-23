import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from app.models import Order, User
from app.schemas import OrderCreate

ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # prevents memory runaway


async def enqueue_order(order: OrderCreate):
    print(f"📥 Enqueued order: {order.message}")
    """Put a parsed order into queue."""
    await ORDER_QUEUE.put(order)


async def enrich_order_with_user(session: AsyncSession, order_dict: dict) -> dict:
    """
    Look up user table by uuid, add alias, legalEntityshortName,
    and fill b_client/o_client, bids/offers.
    """
    sender_uuid = order_dict.get("sender_uuid")
    # requester_uuid = order_dict.get("requester_uuid")

    uuid_to_lookup = sender_uuid 
    if not uuid_to_lookup:
        return order_dict

    result = await session.execute(select(User).where(User.uuid == str(uuid_to_lookup)))
    user = result.scalar_one_or_none()
    if user:
        order_dict["alias"] = user.alias
        order_dict["legalEntityShortName"] = user.legalEntityShortName
        order_dict["tpUserUidTrader"] = user.tpUserUID
        order_dict["tpPostingIdRequester"] = user.tpPostingID
        order_dict["uuidRequester"] = user.uuid

    return order_dict


async def order_worker(session_factory, batch_size=500, flush_interval=0.5):
    """
    Worker: drains ORDER_QUEUE, inserts in batches.
    Handles 1 message, hundreds, or thousands.
    """
    while True:
        batch: list[OrderCreate] = []
        try:
            # Collect up to batch_size or until timeout
            for _ in range(batch_size):
                item = await asyncio.wait_for(ORDER_QUEUE.get(), timeout=flush_interval)
                batch.append(item)
        except asyncio.TimeoutError:
            pass  # no more orders right now

        if not batch:
            continue

        dicts = []
        async with session_factory() as session:
            for item in batch:
                order_dict = {
                    "orderId": str(uuid.uuid4()),
                    "eventId": item.eventId,
                    "message": item.message,
                    # "timestamp": item.timestamp,
                    "sender_uuid": str(item.sender_uuid) if item.sender_uuid else None,
                    "requester_uuid": str(item.requester_uuid) if item.requester_uuid else None,
                    "expiryDate": item.expiryDate,
                    "strategyID": item.strategyID,
                    "contractId": item.contractId,
                    "orderType": item.orderType,
                    # "orderID": item.orderID,
                    "state": item.state,
                    "buySell": item.buySell,
                    "price": item.price,
                    "basis": item.basis,
                    "linkedOrderID": item.linkedOrderID,
                    "refInstrument": item.refInstrument,
                    "refPrice": item.refPrice,
                    "response": item.response,
                    "message_timestamp": item.timestamp,
                    # placeholders for enrichment
                    "alias": None,
                    "legalEntityShortName": None,
                    "tpUserUidTrader": None,
                    "tpPostingIdRequester": None,
                    "uuidRequester": None,
                }
  
                # ✅ enrich with user info + buyer/seller fields
                order_dict = await enrich_order_with_user(session, order_dict)
                dicts.append(order_dict)

   # ✅ Only commit once here, no nested begin()
            await session.execute(insert(Order), dicts)
            await session.commit()

        # Mark tasks done
        for _ in batch:
            ORDER_QUEUE.task_done()
