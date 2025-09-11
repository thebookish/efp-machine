from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Text,Column, CheckConstraint
from datetime import datetime
from sqlalchemy.sql import func

Base = declarative_base()




# class Order(Base):
#     __tablename__ = "orders"

#     id = Column(String, primary_key=True, index=True)
#     message = Column(String, nullable=False)
#     orderType = Column(String, nullable=False)
#     buySell = Column(String, nullable=False)
#     quantity = Column(Float, nullable=False)
#     price = Column(Float, nullable=False)
#     basis = Column(Float, nullable=False)
#     strategyDisplayName = Column(String, nullable=False)
#     contractId = Column(String, nullable=False)
#     expiryDate = Column(String, nullable=False)
#     response = Column(Text, nullable=True)       # empty by default
#     timestamp = Column(DateTime(timezone=True), nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    # From your “fixed user table”
    uuid = Column(String, primary_key=True, index=True)          # e.g. "159890"
    shortName = Column(String, nullable=True)                    # PhilippeLaget
    userName = Column(String, nullable=True)                     # "Philippe Laget"
    alias = Column(String, nullable=True)                        # "PL"
    tpPostingID = Column(String, nullable=True)
    tpUserUID = Column(String, nullable=True)
    tpDdeskUID = Column(String, nullable=True)
    legalEntity = Column(String, nullable=True)                  # "Merrill Lynch International"
    legalEntityshortName = Column(String, nullable=True)         # "ML"
    role = Column(String, nullable=True)                         # Trader / Broker
    firmId = Column(String, nullable=True)                       # "9001"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # CSV fields (all nullable, since sometimes missing)
    content_event_eventId = Column(String, nullable=True)
    content_event_messages_0_message = Column(Text, nullable=True)
    content_event_messages_0_timestamp = Column(String, nullable=True)
    content_event_messages_0_sender_uuid = Column(String, nullable=True)
    requester_uuid = Column(String, nullable=True)
    eurexContractCode = Column(String, nullable=True)
    expiryDate = Column(String, nullable=True)
    contractISIN = Column(String, nullable=True)
    primaryAssetClass = Column(String, nullable=True)
    baseProduct = Column(String, nullable=True)
    subProduct = Column(String, nullable=True)
    eurexProductISIN = Column(String, nullable=True)
    underlyingIndex = Column(String, nullable=True)
    underlyingIndexISIN = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    strategyID = Column(String, nullable=True)
    strategyDescription = Column(Text, nullable=True)
    tradeable_Id = Column(String, nullable=True)
    contractId = Column(String, nullable=True)
    contractName = Column(String, nullable=True)
    strategyID_1 = Column(String, nullable=True)
    strategyDisplayName = Column(String, nullable=True)
    strategyBrandName = Column(String, nullable=True)
    orderType = Column(String, nullable=True)
    orderID = Column(String, nullable=True)
    state = Column(String, nullable=True)
    buySell = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    basis = Column(Float, nullable=True)
    linkedOrderID = Column(String, nullable=True)
    refInstrument = Column(String, nullable=True)
    refPrice = Column(Float, nullable=True)

    # Additional fields
    b_client= Column(Text, nullable=True)
    o_client= Column(Text, nullable=True)
    bids= Column(Text, nullable=True)
    indicatives= Column(Text, nullable=True)
    offers= Column(Text, nullable=True)
    pub_bid= Column(Text, nullable=True)
    pub_offer= Column(Text, nullable=True)
    # NEW: enrichment from users by UUID
    alias = Column(String, nullable=True)
    legalEntityshortName = Column(String, nullable=True)
    response = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=True)
class EfpRun(Base):
    __tablename__ = 'efp_run'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(20))
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    offer: Mapped[float | None] = mapped_column(Float, nullable=True)
    cash_ref: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Recap(Base):
    __tablename__ = 'recap'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Float)
    lots: Mapped[int] = mapped_column(Integer)
    cash_ref: Mapped[float | None] = mapped_column(Float, nullable=True)
    recap_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CashLevel(Base):
    __tablename__ = 'cash_level'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(20))
    level: Mapped[float] = mapped_column(Float)
    as_of: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DailyClose(Base):
    __tablename__ = 'daily_close'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    index_name: Mapped[str] = mapped_column(String(20))
    level: Mapped[float] = mapped_column(Float)
    as_of_date: Mapped[datetime] = mapped_column(DateTime)

class BlotterTrade(Base):
    __tablename__ = "blotter_trades"

    id = Column(Integer, primary_key=True, index=True)
    side = Column(String, nullable=False)   # BUY / SELL
    index_name = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
