

# from fastapi import (
#     APIRouter,
#     Depends,
#     UploadFile,
#     File,
#     HTTPException,
#     WebSocket,
#     WebSocketDisconnect,
# )
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# import uuid, asyncio
# import pandas as pd

# from app.deps import get_db
# from app.models import Order
# from app.schemas import OrderResponse, OrderUpdate, OrderCreate
# from app.services.order_ingest import enqueue_order

# router = APIRouter(prefix="/api/orders", tags=["orders"])


# # --- WebSocket manager ---
# class OrdersWSManager:
#     def __init__(self):
#         self._lock = asyncio.Lock()
#         self.active: set[WebSocket] = set()

#     async def connect(self, ws: WebSocket):
#         await ws.accept()
#         async with self._lock:
#             self.active.add(ws)

#     async def disconnect(self, ws: WebSocket):
#         async with self._lock:
#             if ws in self.active:
#                 self.active.remove(ws)

#     async def broadcast_json(self, message: dict):
#         dead = []
#         async with self._lock:
#             for ws in list(self.active):
#                 try:
#                     await ws.send_json(message)
#                 except Exception:
#                     dead.append(ws)
#             for ws in dead:
#                 self.active.discard(ws)


# manager = OrdersWSManager()


# # --- Helpers ---
# async def _fetch_orders(db: AsyncSession):
#     result = await db.execute(select(Order).order_by(Order.created_at.desc()))
#     return list(result.scalars().all())


# def _serialize_orders(orders: list[Order]) -> list[dict]:
#     return [
#         OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
#         for o in orders
#     ]


# async def _push_full_list(db: AsyncSession):
#     orders = await _fetch_orders(db)
#     await manager.broadcast_json(
#         {"type": "orders_list", "payload": _serialize_orders(orders)}
#     )


# # --- WebSocket feed ---
# @router.websocket("/ws")
# async def orders_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
#     await manager.connect(ws)
#     try:
#         await ws.send_json(
#             {"type": "orders_list", "payload": _serialize_orders(await _fetch_orders(db))}
#         )
#         while True:
#             await asyncio.sleep(60)
#     except WebSocketDisconnect:
#         await manager.disconnect(ws)
#     except Exception:
#         await manager.disconnect(ws)
#         try:
#             await ws.close()
#         except Exception:
#             pass

# # --- Normalizer for CSV records ---
# def normalize_record(rec: dict) -> dict:
#     """Ensure all required fields have correct types (esp. str)."""
#     str_fields = {
#         "content_event_eventId",
#         "content_event_messages_0_message",
#         "content_event_messages_0_timestamp",
#         "content_event_messages_0_sender_uuid",
#         "requester_uuid",
#         "strategyID",
#         "contractId",
#         "orderType",
#         "orderID",
#         "state",
#         "buySell",
#         "linkedOrderID",
#         "refInstrument",
#     }

#     fixed = {}
#     for k, v in rec.items():
#         if v is None or (isinstance(v, float) and pd.isna(v)):
#             fixed[k] = None
#         elif k in str_fields:
#             fixed[k] = str(v)  # force cast to string
#         else:
#             fixed[k] = v
#     return fixed
# # --- Upload CSV ---
# @router.post("/upload")
# async def upload_csv_file(file: UploadFile = File(...)):
#     if not file.filename.endswith(".csv"):
#         raise HTTPException(status_code=400, detail="Only .csv files allowed")
#     try:
#         df = pd.read_csv(file.file)

#         # normalize headers
#         df.columns = [c.replace(".", "_") for c in df.columns]
#         df.columns = [c.replace(" ", "_") for c in df.columns]
#         df = df.where(pd.notnull(df), None)

#         records = df.to_dict(orient="records")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to parse CSV: {e}")

#     from app.services.order_ingest import enqueue_order
#     inserted = 0
#     for rec in records:
#         try:
#             normalized = normalize_record(rec)
#             order = OrderCreate(**normalized)
#             await enqueue_order(order)
#             inserted += 1
#         except Exception as e:
#             print(f"⚠️ Skipping row: {e}")

#     return {"queued": inserted, "status": "accepted"}



# # --- List orders ---
# @router.get("/list", response_model=list[OrderResponse])
# async def list_orders(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Order).order_by(Order.created_at.desc()))
#     return result.scalars().all()


# # --- Edit order ---
# @router.put("/edit/{order_id}", response_model=OrderResponse)
# async def edit_order(order_id: str, updates: OrderUpdate, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Order).where(Order.id == order_id))
#     order = result.scalar_one_or_none()
#     if not order:
#         raise HTTPException(status_code=404, detail="Order not found")

#     for field, value in updates.model_dump(exclude_unset=True).items():
#         setattr(order, field, value)

#     await db.commit()
#     await db.refresh(order)
#     await _push_full_list(db)
#     return order
from fastapi import HTTPException
from app.services.fetch_messages import fetch_and_process_messages
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio, httpx
import json
from app.deps import get_db, AsyncSessionLocal
from app.models import Order
from app.schemas import OrderResponse, OrderUpdate
from app.services.order_ingest import enqueue_order
from app.services.parse import parse_single_message
from app.services.simple_parser import simple_parse_message

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrdersWSManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self.active:
                self.active.remove(ws)

    async def broadcast_json(self, message: dict):
        dead = []
        async with self._lock:
            for ws in list(self.active):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active.discard(ws)


manager = OrdersWSManager()


async def _fetch_orders(db: AsyncSession):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return list(result.scalars().all())


def _serialize_orders(orders: list[Order]) -> list[dict]:
    return [
        OrderResponse.model_validate(o, from_attributes=True).model_dump(mode="json")
        for o in orders
    ]


async def _push_full_list(db: AsyncSession):
    orders = await _fetch_orders(db)
    await manager.broadcast_json(
        {"type": "orders_list", "payload": _serialize_orders(orders)}
    )


@router.websocket("/ws")
async def orders_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await manager.connect(ws)
    try:
        await ws.send_json(
            {"type": "orders_list", "payload": _serialize_orders(await _fetch_orders(db))}
        )
        while True:
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        await manager.disconnect(ws)
        try:
            await ws.close()
        except Exception:
            pass



@router.post("/fetch")
async def fetch_orders_from_api(db: AsyncSession = Depends(get_db)):
    """
    Fetch new messages from external API, parse, and enqueue into DB.
    """
    try:
        result = await fetch_and_process_messages()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed fetching messages: {e}")
    
# --- List orders ---
@router.get("/list", response_model=list[OrderResponse])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).order_by(Order.created_at.desc()))
    return result.scalars().all()


# --- Edit order ---
@router.put("/edit/{order_id}", response_model=OrderResponse)
async def edit_order(order_id: str, updates: OrderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.orderId == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = updates.model_dump(exclude_unset=True)

    # ✅ If response is being updated, parse it and auto-update fields
    if "response" in update_data and update_data["response"]:
      

        parsed = simple_parse_message(update_data["response"])
        if parsed:
            order.contractId = parsed["contractId"]
            order.expiryDate = parsed["expiryDate"]
            order.buySell = parsed["buySell"]
            order.price = parsed["price"]
            order.basis = parsed["basis"]

    # ✅ Apply other updates
    for field, value in update_data.items():
        setattr(order, field, value)

    await db.commit()
    await db.refresh(order)
    await _push_full_list(db)
    return order

