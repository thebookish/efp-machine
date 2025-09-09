from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Text,Column, CheckConstraint
from datetime import datetime
from sqlalchemy.sql import func

Base = declarative_base()




class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    message = Column(String, nullable=False)
    orderType = Column(String, default="SINGLE")
    buySell = Column(String, nullable=False)   # BUY / SELL
    quantity = Column(Float, default=1.0)
    price = Column(Float, nullable=False)
    basis = Column(Float, nullable=False)
    strategyDisplayName = Column(String, default="TRF")
    contractId = Column(String, nullable=False)  # e.g. SX5E
    expiryDate = Column(String, nullable=False)  # e.g. DEC26
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
