from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import field_validator


class RegisterSchema(BaseModel):

    username: str

    email: EmailStr

    password: str


class LoginSchema(BaseModel):

    username: str

    password: str


class UserResponse(BaseModel):

    id: int

    username: str

    email: EmailStr

    class Config:
        from_attributes = True


class InstrumentResponse(BaseModel):

    instrument_token: int

    tradingsymbol: str

    name: str | None

    exchange: str

    segment: str

    expiry: date | None

    strike: float | None

    instrument_type: str

    lot_size: int

    class Config:
        from_attributes = True


class OptionChainRow(BaseModel):

    strike: float

    call: InstrumentResponse | None

    put: InstrumentResponse | None

    class Config:
        from_attributes = True


class TradeCreate(BaseModel):

    instrument_token: int

    transaction_type: Literal["BUY", "SELL"]

    product: Literal["MIS", "CNC", "NRML"]

    quantity: int = Field(gt=0)

    price: Decimal = Field(gt=0)

    trade_date: date | None = None

    @field_validator("trade_date")
    @classmethod
    def trade_date_not_in_future(cls, value):

        if value is not None and value > date.today():
            raise ValueError("trade_date cannot be in the future")

        return value


class TradeResponse(BaseModel):

    id: int

    instrument_token: int

    transaction_type: str

    product: str

    quantity: int

    price: float

    trade_date: date

    traded_at: datetime

    carried_forward: bool

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):

    instrument_token: int

    tradingsymbol: str

    exchange: str

    product: str

    quantity: int

    average_price: float

    last_price: float | None

    unrealized_pnl: float


class HoldingResponse(BaseModel):

    instrument_token: int

    tradingsymbol: str

    exchange: str

    quantity: int

    average_price: float

    last_price: float | None

    unrealized_pnl: float


class EODCarryForwardResponse(BaseModel):

    trades_carried: int

    positions_updated: int