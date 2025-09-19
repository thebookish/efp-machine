import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from app.models import Order, User
from app.schemas import OrderCreate

ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # prevents memory runaway


async def enqueue_order(order: OrderCreate):
    """Put a parsed order into queue."""
    await ORDER_QUEUE.put(order)


async def enrich_order_with_user(session: AsyncSession, order_dict: dict) -> dict:
    """
    Look up user table by uuid, add alias, legalEntityshortName,
    and fill b_client/o_client, bids/offers.
    """
    sender_uuid = order_dict.get("content_event_messages_0_sender_uuid")
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
     

        # # Business rules
        # if order_dict.get("buySell") == "Buy":
        #     order_dict["b_client"] = user.legalEntityShortName
        #     order_dict["o_client"] = None
        #     order_dict["bids"] = order_dict.get("price")
        #     order_dict["offers"] = None
        # elif order_dict.get("buySell") == "Sell":
        #     order_dict["b_client"] = None
        #     order_dict["o_client"] = user.legalEntityShortName
        #     order_dict["bids"] = None
        #     order_dict["offers"] = order_dict.get("price")

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
                    "id": str(uuid.uuid4()),
                    "content_event_eventId": item.content_event_eventId,
                    "content_event_messages_0_message": item.content_event_messages_0_message,
                    "content_event_messages_0_timestamp": item.content_event_messages_0_timestamp,
                    "content_event_messages_0_sender_uuid": str(item.content_event_messages_0_sender_uuid) if item.content_event_messages_0_sender_uuid else None,
                    "requester_uuid": str(item.requester_uuid) if item.requester_uuid else None,
                    # "eurexContractCode": item.eurexContractCode,
                    "expiryDate": item.expiryDate,
                    # "contractISIN": item.contractISIN,
                    # "primaryAssetClass": item.primaryAssetClass,
                    # "baseProduct": item.baseProduct,
                    # "subProduct": item.subProduct,
                    # "eurexProductISIN": item.eurexProductISIN,
                    # "underlyingIndex": item.underlyingIndex,
                    # "underlyingIndexISIN": item.underlyingIndexISIN,
                    # "currency": item.currency,
                    "strategyID": item.strategyID,
                    # "strategyDescription": item.strategyDescription,
                    # "tradeable_Id": item.tradeable_Id,
                    "contractId": item.contractId,
                    # "contractName": item.contractName,
                    # "strategyID_1": item.strategyID_1,
                    # "strategyDisplayName": item.strategyDisplayName,
                    # "strategyBrandName": item.strategyBrandName,
                    "orderType": item.orderType,
                    "orderID": item.orderID,
                    "state": item.state,
                    "buySell": item.buySell,
                    "price": item.price,
                    "basis": 3.75,
                    "linkedOrderID": item.linkedOrderID,
                    "refInstrument": item.refInstrument,
                    "refPrice": item.refPrice,
                    "response": item.response,
                    "timestamp": item.timestamp,
                    # placeholders for enrichment
                    "alias": None,
                    "legalEntityShortName": None,
                    "tpUserUidTrader": None,
                    "tpPostingIdRequester": None,
                    "uuidRequester": None,
                    # "b_client": None,
                    # "o_client": None,
                    # "bids": None,
                    # "offers": None,
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
