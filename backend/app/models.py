from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, Integer,Date, DateTime,JSON, Boolean, Text,Column,Numeric, CheckConstraint
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class BloombergMessage(Base):
    __tablename__ = "bloomberg_messages"

    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    eventId = Column(String, nullable=False, unique=True,primary_key=True,)
    roomId = Column(String, nullable=False)
    originalMessage = Column(Text, nullable=False)

    trader_uuid = Column(String, nullable=False)
    trader_legalEntityShortName = Column(String, nullable=True)
    trader_alias = Column(String, nullable=True)

    original_llm_json = Column(JSON, nullable=True)
    current_json = Column(JSON, nullable=True)

    is_edited = Column(Boolean, default=False)
    messageStatus = Column(String, default="received")  # received/rejected/approved
    source =  Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"

    tradeableId = Column(String, primary_key=True, index=True)   # e.g. SX5E_TRF_ICAP_P133IYzI003c25
    expiryDate = Column(Date, nullable=False)                    # ISO date (YYYY-MM-DD)
    code = Column(String, nullable=False)                        # contract month code e.g. Z25
    currency = Column(String, nullable=False)                    # e.g. EUR
    contractId = Column(String, nullable=False)                  # underlying contract/index
    strategyDisplayName = Column(String, nullable=False)          # e.g. TRF
    refInstrument = Column(String, nullable=True)                # optional
    refPrice = Column(Float, nullable=True)                      # optional

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
    legalEntityShortName = Column(String, nullable=True)         # "ML"
    role = Column(String, nullable=True)                         # Trader / Broker
    firmId = Column(String, nullable=True)                       # "9001"


class Order(Base):
    __tablename__ = "orders"

    orderId = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    lastUpdated = Column(DateTime(timezone=True), onupdate=func.now())

    eventId = Column(String, nullable=False)
    linkedOrderID = Column(String, nullable=False)
    message = Column(String, nullable=False)
    expiryDate = Column(String, nullable=False)
    strategyID = Column(String, nullable=True)
    contractId = Column(String, nullable=False)
    side = Column(String, nullable=False)  # BUY/SELL
    price = Column(Float, nullable=False)
    basis = Column(Float, nullable=False)

    orderStatus = Column(String, default="active")
    orderStatusHistory = Column(JSON, default=list)

    traderUuid = Column(String, nullable=False)
    traderLegalEntityShortName = Column(String, nullable=True)
    traderAlias = Column(String, nullable=True)

    refPrice = Column(Float, nullable=True)

    reminderEnabled = Column(Boolean, default=False)
    reminderCount = Column(Integer, default=0)
    nextReminderDue = Column(DateTime(timezone=True), nullable=True)
    lastReminderSent = Column(DateTime(timezone=True), nullable=True)
    reminderHistory = Column(JSON, default=list)

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
