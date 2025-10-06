# backend/app/schemas.py
from pydantic import BaseModel,Field
from datetime import datetime, date
from typing import Optional, Any, List

class BloombergMessageBase(BaseModel):
    eventId: str
    roomId: str
    originalMessage: str
    trader_uuid: str
    trader_legalEntityShortName: Optional[str] = None
    trader_alias: Optional[str] = None
    original_llm_json: Optional[Any] = None
    current_json: Optional[Any] = None
    is_edited: Optional[bool] = False
    messageStatus: str = "received"   # NEW: received / rejected / approved
    source: Optional[str] = None
    isTarget: bool = False


class BloombergMessageCreate(BloombergMessageBase):
    pass


class BloombergMessageUpdate(BaseModel):
    current_json: Optional[Any] = None
    is_edited: Optional[bool] = None
    messageStatus: Optional[str] = None


class BloombergMessageResponse(BloombergMessageBase):
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstrumentBase(BaseModel):
    expiryDate: date
    code: str
    currency: str
    contractId: str
    strategyDisplayName: str
    refInstrument: Optional[str] = None
    refPrice: Optional[float] = None


class InstrumentCreate(InstrumentBase):
    tradeableId: str


class InstrumentResponse(InstrumentBase):
    tradeableId: str

    class Config:
        from_attributes = True 

# -------- Users --------
class UserCreate(BaseModel):
    uuid: str
    shortName: Optional[str] = None
    userName: Optional[str] = None
    alias: Optional[str] = None
    tpPostingID: Optional[str] = None
    tpUserUID: Optional[str] = None
    tpDdeskUID: Optional[str] = None
    legalEntity: Optional[str] = None
    legalEntityShortName: Optional[str] = None
    role: Optional[str] = None
    firmId: Optional[str] = None


class UserResponse(UserCreate):
    created_at: datetime

class OrderStatusEntry(BaseModel):
    orderStatus: str
    timestamp: datetime


class OrderCreate(BaseModel):
    eventId: str
    linkedOrderID: str
    message: str
    expiryDate: str
    strategyID: Optional[str] = None
    contractId: str
    side: str
    price: float
    basis: float
    orderStatus: str = "active"
    traderUuid: str
    traderLegalEntityShortName: Optional[str] = None
    traderAlias: Optional[str] = None
    refPrice: Optional[float] = None
    orderStatusHistory: List[OrderStatusEntry] = []
    reminderEnabled: bool = False
    reminderCount: int = 0
    nextReminderDue: Optional[datetime] = None
    lastReminderSent: Optional[datetime] = None
    reminderHistory: List[dict] = []
    lastUpdated: Optional[datetime] = None
    isTarget: bool = False
    targetPrice: Optional[float] = None


class OrderUpdate(BaseModel):
    orderStatus: Optional[str] = None
    orderStatusHistory: Optional[List[OrderStatusEntry]] = None
    reminderEnabled: Optional[bool] = None
    reminderCount: Optional[int] = None
    nextReminderDue: Optional[datetime] = None
    lastReminderSent: Optional[datetime] = None
    reminderHistory: Optional[List[dict]] = None
    lastUpdated: Optional[datetime] = None
    isTarget: bool = False
    targetPrice: Optional[float] = None


class OrderResponse(OrderCreate):
    orderId: str
    createdAt: datetime

    class Config:
        from_attributes = True


class SlackMessageRequest(BaseModel):
    channel: str
    text: str

class SlackMessageResponse(BaseModel):
    ok: bool
    channel: str | None = None
    ts: str | None = None
    error: str | None = None
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
