# backend/app/schemas.py
from pydantic import BaseModel,Field
from datetime import datetime
from typing import Optional

class OrderCreate(BaseModel):
    client_provided_id: str
    symbol: str
    expiry: str
    side: str
    quantity: float
    price: float
    basis: float


class OrderResponse(OrderCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
# -------- Trades --------
class TradeRequest(BaseModel):
    index: str
    price: float
    lots: int
    cash_ref: float


class TradeResponse(BaseModel):
    id: int
    index: str
    price: float
    lots: int
    cash_ref: float
    status: str


# -------- EFP Price Update --------

class UpdatePriceRequest(BaseModel):
    index: str
    bid: Optional[float] = None
    offer: Optional[float] = None
    cash_ref: Optional[float] = None
    dean_confirm: bool = False


# -------- Cash Ref --------
class CashRefRequest(BaseModel):
    index: str
    cash_ref: float


# -------- Propose Mid --------
class ProposeMidRequest(BaseModel):
    index: str
    mid: float
    width: Optional[float] = None


# -------- Confirm Worsening --------
class ConfirmRequest(BaseModel):
    index: str
    note: Optional[str] = None


# -------- Publish Run --------
class PublishRequest(BaseModel):
    name: str


# -------- Expiry --------
class ExpiryRequest(BaseModel):
    index: str
    date: str   # ISO date string


# -------- Generic Recap --------
class RecapRequest(BaseModel):
    text: str

class EfpRow(BaseModel):
    index: str = Field(..., alias='index_name')
    bid: Optional[float] = None
    offer: Optional[float] = None
    cash_ref: Optional[float] = None
    
class CommandResult(BaseModel):
    ok: bool
    detail: str
    recap: Optional[str] = None
    requires_cash_ref: bool = False
    requires_confirmation: bool = False
    updated_run: Optional[list[EfpRow]] = None

class BlotterTradeBase(BaseModel):
    side: str
    index_name: str
    qty: int
    price: float


class BlotterTradeResponse(BaseModel):
    id: int
    side: str
    index_name: str
    qty: int
    avg_price: float
    created_at: datetime

    class Config:
        from_attributes = True   # ✅ allows ORM -> schema conversion


class BlotterRemoveRequest(BaseModel):
    trade_id: int
