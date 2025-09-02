from pydantic import BaseModel, Field
from typing import Optional

class EfpRow(BaseModel):
    index: str = Field(..., alias='index_name')
    bid: Optional[float] = None
    offer: Optional[float] = None
    cash_ref: Optional[float] = None

class UpdatePriceRequest(BaseModel):
    index: str
    bid: Optional[float] = None
    offer: Optional[float] = None
    cash_ref: Optional[float] = None
    dean_confirm: bool = False

class TradeRequest(BaseModel):
    index: str
    price: float
    lots: int
    cash_ref: Optional[float] = None

class AiUserMessage(BaseModel):
    message: str

class CommandResult(BaseModel):
    ok: bool
    detail: str
    recap: Optional[str] = None
    requires_cash_ref: bool = False
    requires_confirmation: bool = False
    updated_run: Optional[list[EfpRow]] = None
