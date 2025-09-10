# app/services/order_ingest.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.models import Order
from app.schemas import OrderCreate

ORDER_QUEUE = asyncio.Queue(maxsize=10000)  # prevents memory runaway

async def enqueue_order(order: OrderCreate):
    """Put a parsed order into queue."""
    await ORDER_QUEUE.put(order)

async def order_worker(session_factory, batch_size=500, flush_interval=0.5):
    """Worker: drains ORDER_QUEUE, inserts in batches."""
    while True:
        batch: list[OrderCreate] = []
        try:
            # Collect up to batch_size or until timeout
            for _ in range(batch_size):
                item = await asyncio.wait_for(ORDER_QUEUE.get(), timeout=flush_interval)
                batch.append(item)
        except asyncio.TimeoutError:
            pass  # no more orders right now

        if batch:
            dicts = [
                {
                    "id": item.id,
                    "message": item.message,
                    "orderType": item.orderType,
                    "buySell": item.buySell,
                    "quantity": item.quantity,
                    "price": item.price,
                    "basis": item.basis,
                    "strategyDisplayName": item.strategyDisplayName,
                    "contractId": item.contractId,
                    "expiryDate": item.expiryDate,
                }
                for item in batch
            ]

            async with session_factory() as session:
                async with session.begin():
                    await session.execute(insert(Order), dicts)

            # mark as done
            for _ in batch:
                ORDER_QUEUE.task_done()
