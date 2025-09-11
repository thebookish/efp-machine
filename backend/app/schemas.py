# backend/app/schemas.py
from pydantic import BaseModel,Field
from datetime import datetime
from typing import Optional

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

class OrderCreate(BaseModel):
    content_event_eventId: Optional[str] = None
    content_event_messages_0_message: Optional[str] = None
    content_event_messages_0_timestamp: Optional[str] = None
    content_event_messages_0_sender_uuid: Optional[str] = None
    requester_uuid: Optional[str] = None
    eurexContractCode: Optional[str] = None
    expiryDate: Optional[str] = None
    contractISIN: Optional[str] = None
    primaryAssetClass: Optional[str] = None
    baseProduct: Optional[str] = None
    subProduct: Optional[str] = None
    eurexProductISIN: Optional[str] = None
    underlyingIndex: Optional[str] = None
    underlyingIndexISIN: Optional[str] = None
    currency: Optional[str] = None
    strategyID: Optional[str] = None
    strategyDescription: Optional[str] = None
    tradeable_Id: Optional[str] = None
    contractId: Optional[str] = None
    contractName: Optional[str] = None
    strategyID_1: Optional[str] = None
    strategyDisplayName: Optional[str] = None
    strategyBrandName: Optional[str] = None
    orderType: Optional[str] = None
    orderID: Optional[str] = None
    state: Optional[str] = None
    buySell: Optional[str] = None
    price: Optional[float] = None
    basis: Optional[float] = None
    linkedOrderID: Optional[str] = None
    refInstrument: Optional[str] = None
    refPrice: Optional[float] = None
    b_client: Optional[str] = None
    o_client: Optional[str] = None
    bids: Optional[str] = None
    indicatives: Optional[str] = None
    offers: Optional[str] = None
    pub_bid: Optional[str] = None
    pub_offer: Optional[str] = None
    alias: Optional[str] = None
    legalEntitiShortName: Optional[str] = None
    response: Optional[str] = None
    timestamp: Optional[datetime] = None


class OrderUpdate(BaseModel):
    # All fields optional for editing
    content_event_eventId: Optional[str] = None
    content_event_messages_0_message: Optional[str] = None
    content_event_messages_0_timestamp: Optional[str] = None
    content_event_messages_0_sender_uuid: Optional[str] = None
    requester_uuid: Optional[str] = None
    eurexContractCode: Optional[str] = None
    expiryDate: Optional[str] = None
    contractISIN: Optional[str] = None
    primaryAssetClass: Optional[str] = None
    baseProduct: Optional[str] = None
    subProduct: Optional[str] = None
    eurexProductISIN: Optional[str] = None
    underlyingIndex: Optional[str] = None
    underlyingIndexISIN: Optional[str] = None
    currency: Optional[str] = None
    strategyID: Optional[str] = None
    strategyDescription: Optional[str] = None
    tradeableId: Optional[str] = None
    contractId: Optional[str] = None
    contractName: Optional[str] = None
    strategyID_1: Optional[str] = None
    strategyDisplayName: Optional[str] = None
    strategyBrandName: Optional[str] = None
    orderType: Optional[str] = None
    orderID: Optional[str] = None
    state: Optional[str] = None
    buySell: Optional[str] = None
    price: Optional[float] = None
    basis: Optional[float] = None
    linkedOrderID: Optional[str] = None
    refInstrument: Optional[str] = None
    refPrice: Optional[float] = None
    b_client: Optional[str] = None
    o_client: Optional[str] = None
    bids: Optional[str] = None
    indicatives: Optional[str] = None
    offers: Optional[str] = None
    pub_bid: Optional[str] = None
    pub_offer: Optional[str] = None
    alias: Optional[str] = None
    legalEntitiShortName: Optional[str] = None
    response: Optional[str] = None
    timestamp: Optional[datetime] = None


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
