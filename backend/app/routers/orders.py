# import uuid
# import json
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from app.deps import get_db
# from app.models import Order
# from app.schemas import OrderResponse
# from app.services.parse import parse_bbg_message

# router = APIRouter(prefix="/api/orders", tags=["orders"])

# @router.post("/load")
# async def load_bbg_data(db: AsyncSession = Depends(get_db)):
#     try:
#         with open("bbg_data.json", "r") as f:
#             events = json.load(f)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to load JSON: {e}")

#     inserted = 0
#     for ev in events:
#         parsed = parse_bbg_message(ev)
#         if not parsed:
#             continue

#         # Skip if already exists
#         exists = await db.execute(
#             select(Order).where(Order.client_provided_id == parsed.client_provided_id)
#         )
#         if exists.scalar_one_or_none():
#             continue

#         order = Order(
#             id=str(uuid.uuid4()),
#             client_provided_id=parsed.client_provided_id,
#             symbol=parsed.symbol,
#             side=parsed.side,
#             basis=parsed.basis,
#             price=parsed.price,
#         )
#         db.add(order)
#         inserted += 1

#     await db.commit()
#     return {"inserted": inserted, "status": "ok"}

# @router.get("/list", response_model=list[OrderResponse])
# async def list_orders(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Order).order_by(Order.created_at.desc()))
#     return result.scalars().all()
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid, json

from app.deps import get_db
from app.models import Order
from app.schemas import OrderResponse, OrderCreate
from app.services.parse import parse_bbg_message

router = APIRouter(prefix="/api/orders", tags=["orders"])

@router.post("/upload")
async def upload_bbg_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed")

    try:
        contents = await file.read()
        events = json.loads(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {e}")

    inserted = 0
    for ev in events:
        parsed = parse_bbg_message(ev)
        if not parsed:
            continue

        # Skip duplicates
        exists = await db.execute(
            select(Order).where(Order.client_provided_id == parsed.client_provided_id)
        )
        if exists.scalar_one_or_none():
            continue

        order = Order(
            id=str(uuid.uuid4()),
            client_provided_id=parsed.client_provided_id,
            symbol=parsed.symbol,
            side=parsed.side,
            basis= parsed.basis,
            price=parsed.price,
        )
        db.add(order)
        inserted += 1

    await db.commit()
    return {"inserted": inserted, "status": "ok"}
