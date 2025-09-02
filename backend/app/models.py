from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Text
from datetime import datetime

Base = declarative_base()

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
