# # app/services/order_ingest.py
# import asyncio
# import uuid
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import insert
# from app.models import Order
# from app.schemas import OrderCreate

# ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # prevents memory runaway

# async def enqueue_order(order: OrderCreate):
#     """Put a parsed order into queue."""
#     await ORDER_QUEUE.put(order)

# async def order_worker(session_factory, batch_size=500, flush_interval=0.5):
#     """Worker: drains ORDER_QUEUE, inserts in batches."""
#     while True:
#         batch: list[OrderCreate] = []
#         try:
#             # Collect up to batch_size or until timeout
#             for _ in range(batch_size):
#                 item = await asyncio.wait_for(ORDER_QUEUE.get(), timeout=flush_interval)
#                 batch.append(item)
#         except asyncio.TimeoutError:
#             pass  # no more orders right now

#         if batch:
#             dicts = [
#                 {
#                     "id": str(uuid.uuid4()),
#                     "message": item.message,
#                     "orderType": item.orderType,
#                     "buySell": item.buySell,
#                     "quantity": item.quantity,
#                     "price": item.price,
#                     "basis": item.basis,
#                     "strategyDisplayName": item.strategyDisplayName,
#                     "contractId": item.contractId,
#                     "expiryDate": item.expiryDate,
#                     "response": item.response,
#                     "timestamp": item.timestamp,
#                 }
#                 for item in batch
#             ]

#             async with session_factory() as session:
#                 async with session.begin():
#                     await session.execute(insert(Order), dicts)

#             # mark as done
#             for _ in batch:
#                 ORDER_QUEUE.task_done()
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from app.models import Order, User
from app.schemas import OrderCreate

ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # buffer


async def enqueue_order(order: OrderCreate):
    """Put a parsed order into queue."""
    await ORDER_QUEUE.put(order)


async def enrich_order_with_user(session: AsyncSession, order_dict: dict) -> dict:
    """
    Look up user table by uuid, add alias and legalEntityshortName.
    """
    sender_uuid = order_dict.get("content_event_messages_0_sender_uuid")
    requester_uuid = order_dict.get("requester_uuid")

    # Prefer sender uuid if present, else requester
    uuid_to_lookup = sender_uuid or requester_uuid
    if not uuid_to_lookup:
        return order_dict

    result = await session.execute(select(User).where(User.uuid == str(uuid_to_lookup)))
    user = result.scalar_one_or_none()
    if user:
        order_dict["alias"] = user.alias
        order_dict["legalEntityshortName"] = user.legalEntityshortName

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

        # Convert to dicts
        dicts = []
        async with session_factory() as session:
            for item in batch:
                order_dict = {
                    "id": str(uuid.uuid4()),
                    "content_event_eventId": item.content_event_eventId,
                    "content_event_messages_0_message": item.content_event_messages_0_message,
                    "content_event_messages_0_timestamp": item.content_event_messages_0_timestamp,
                    "content_event_messages_0_sender_uuid": str(item.content_event_messages_0_sender_uuid) if item.content_event_messages_0_sender_uuid else None,
                    "requester_uuid": str(item.requester_uuid) if item.requester_uuid else None,
                    "eurexContractCode": item.eurexContractCode,
                    "expiryDate": item.expiryDate,
                    "contractISIN": item.contractISIN,
                    "primaryAssetClass": item.primaryAssetClass,
                    "baseProduct": item.baseProduct,
                    "subProduct": item.subProduct,
                    "eurexProductISIN": item.eurexProductISIN,
                    "underlyingIndex": item.underlyingIndex,
                    "underlyingIndexISIN": item.underlyingIndexISIN,
                    "currency": item.currency,
                    "strategyID": item.strategyID,
                    "strategyDescription": item.strategyDescription,
                    "tradeable_Id": item.tradeable_Id,
                    "contractId": item.contractId,
                    "contractName": item.contractName,
                    "strategyID_1": item.strategyID_1,
                    "strategyDisplayName": item.strategyDisplayName,
                    "strategyBrandName": item.strategyBrandName,
                    "orderType": item.orderType,
                    "orderID": item.orderID,
                    "state": item.state,
                    "buySell": item.buySell,
                    "price": item.price,
                    "basis": item.basis,
                    "linkedOrderID": item.linkedOrderID,
                    "refInstrument": item.refInstrument,
                    "refPrice": item.refPrice,
                    "response": item.response,
                    "timestamp": item.timestamp,
                }

                # ✅ enrich with alias + legalEntityshortName
                order_dict = await enrich_order_with_user(session, order_dict)
                dicts.append(order_dict)

            # Bulk insert
            async with session.begin():
                await session.execute(insert(Order), dicts)

        # Mark tasks done
        for _ in batch:
            ORDER_QUEUE.task_done()
