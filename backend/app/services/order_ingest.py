import asyncio
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, cast, Date
from app.models import Order, User, Instrument
from app.schemas import OrderCreate

ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # prevents memory runaway


async def enqueue_order(order: OrderCreate):
    """Put a parsed order into the queue."""
    print(f"📥 Enqueued order: {order.message}")
    await ORDER_QUEUE.put(order)


async def enrich_order_with_user(session: AsyncSession, order_dict: dict) -> dict:
    """
    Look up user table by uuid and enrich alias + legalEntityShortName.
    """
    trader_uuid = order_dict.get("traderUuid")
    if not trader_uuid:
        return order_dict

    result = await session.execute(select(User).where(User.uuid == str(trader_uuid)))
    user = result.scalar_one_or_none()
    if user:
        order_dict["traderAlias"] = user.alias
        order_dict["traderLegalEntityShortName"] = user.legalEntityShortName

    return order_dict


async def enrich_order_with_instrument(session: AsyncSession, order_dict: dict) -> dict:
    """
    Look up instruments table by contractId + expiryDate, fill strategyID if found.
    """
    contract_id = order_dict.get("contractId")
    expiry = order_dict.get("expiryDate")

    if not contract_id or not expiry:
        return order_dict
    try:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d").date()
    except ValueError:
        print(f"⚠️ Invalid expiry format for order: {expiry}")
        return order_dict
    result = await session.execute(
        select(Instrument).where(
            Instrument.contractId == contract_id,
            Instrument.expiryDate == expiry_date
        )
    )
    instrument = result.scalars().first()
    if instrument:
        order_dict["strategyID"] = instrument.tradeableId
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
            pass

        if not batch:
            continue

        dicts = []
        async with session_factory() as session:
            for item in batch:
                # build order dict based on new schema
                order_dict = {
                    "orderId": str(uuid.uuid4()),
                    "eventId": item.eventId,
                    "linkedOrderID": item.linkedOrderID or item.eventId,
                    "message": item.message,
                    "expiryDate": item.expiryDate,
                    "strategyID": item.strategyID,
                    "contractId": item.contractId,
                    "side": item.side,
                    "price": item.price,
                    "basis": item.basis,
                    "orderStatus": item.orderStatus or "active",
                    "orderStatusHistory": item.orderStatusHistory or [
                        {"orderStatus": "accepted", "timestamp": str(uuid.uuid1())}
                    ],
                    "traderUuid": item.traderUuid,
                    "traderLegalEntityShortName": item.traderLegalEntityShortName,
                    "traderAlias": item.traderAlias,
                    "refPrice": item.refPrice,
                    "isTarget": item.isTarget,
                    "targetPrice": None,
                    "reminderEnabled": item.reminderEnabled or False,
                    "reminderCount": item.reminderCount or 0,
                    "nextReminderDue": item.nextReminderDue,
                    "lastReminderSent": item.lastReminderSent,
                    "reminderHistory": item.reminderHistory or [],
                    "lastUpdated": item.lastUpdated,
                }

                # ✅ enrich with user info
                order_dict = await enrich_order_with_user(session, order_dict)

                # ✅ enrich with instrument strategyID
                order_dict = await enrich_order_with_instrument(session, order_dict)

                dicts.append(order_dict)

            # ✅ commit once per batch
            await session.execute(insert(Order), dicts)
            await session.commit()

        # Mark tasks done
        for _ in batch:
            ORDER_QUEUE.task_done()
