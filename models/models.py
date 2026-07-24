from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import UniqueConstraint
from sqlalchemy.sql import func
from datetime import date, datetime
from zoneinfo import ZoneInfo
from db_ops.db_ops import Base


def ist_now():
    return datetime.now(ZoneInfo("Asia/Kolkata"))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=ist_now)

class Instrument(Base):
    __tablename__ = "instruments"

    instrument_token = Column(BigInteger, primary_key=True)
    exchange_token = Column(BigInteger)
    tradingsymbol = Column(String(50), index=True)
    name = Column(String(100))
    last_price = Column(Numeric(15, 4))
    expiry = Column(Date)
    strike = Column(Numeric(15, 4))
    tick_size = Column(Numeric(10, 4))
    lot_size = Column(Integer)
    instrument_type = Column(String(20))
    segment = Column(String(30), index=True)
    exchange = Column(String(10), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class AppMetadata(Base):
    __tablename__ = "app_metadata"

    key_name = Column(String(100), primary_key=True)

    value = Column(String(255))

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instrument_token = Column(
        BigInteger,
        ForeignKey("instruments.instrument_token"),
        nullable=False,
    )
    transaction_type = Column(String(10), nullable=False)
    product = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    trade_date = Column(Date, nullable=False, default=date.today)
    traded_at = Column(DateTime, nullable=False, default=ist_now)
    carried_forward = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_trades_user_date", "user_id", "trade_date"),
        Index(
            "ix_trades_user_product_carried",
            "user_id",
            "product",
            "carried_forward",
        ),
    )


class CarryforwardPosition(Base):
    __tablename__ = "carryforward_positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instrument_token = Column(
        BigInteger,
        ForeignKey("instruments.instrument_token"),
        nullable=False,
    )
    product = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    average_price = Column(Numeric(15, 4), nullable=False, default=0)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product",
            "instrument_token",
            name="uq_carryforward_user_product_instrument",
        ),
    )
