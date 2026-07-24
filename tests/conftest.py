import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db_ops.db_ops import Base, get_db
from models.models import Instrument
from routers.instruments import router as instrument_router
from routers.positions import router as position_router
from routers.trades import router as trade_router
from routers.users import router as user_router

# Tests must never touch the real MySQL database (it holds real trades) -
# every test gets its own isolated in-memory SQLite DB, and the app under
# test is assembled fresh here rather than importing main.app, since
# importing main.py triggers Base.metadata.create_all() and an instrument
# sync against the real MySQL/Kite endpoints as a side effect.


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield TestSessionLocal

    engine.dispose()


@pytest.fixture()
def client(session_factory):
    app = FastAPI()
    app.include_router(user_router)
    app.include_router(instrument_router)
    app.include_router(trade_router)
    app.include_router(position_router)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def register_user(client):
    def _register(username="trader", email="trader@test.com", password="Secret123!"):
        return client.post(
            "/register",
            json={"username": username, "email": email, "password": password},
        )

    return _register


@pytest.fixture()
def auth_headers(client, register_user):
    register_user()
    r = client.post("/login", data={"username": "trader", "password": "Secret123!"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


EQUITY_TOKEN = 100001
EQUITY_TOKEN_2 = 100002
FUTURE_TOKEN = 100003
CALL_TOKEN = 100004
PUT_TOKEN = 100005


@pytest.fixture()
def seed_instruments(session_factory):
    expiry = date.today() + timedelta(days=10)

    db = session_factory()
    db.add_all([
        Instrument(
            instrument_token=EQUITY_TOKEN, exchange_token=1, tradingsymbol="RELIANCE",
            name="RELIANCE", exchange="NSE", segment="NSE", instrument_type="EQ",
            lot_size=1, last_price=Decimal("2500"),
        ),
        Instrument(
            instrument_token=EQUITY_TOKEN_2, exchange_token=2, tradingsymbol="INFY",
            name="INFY", exchange="NSE", segment="NSE", instrument_type="EQ",
            lot_size=1, last_price=Decimal("1500"),
        ),
        Instrument(
            instrument_token=FUTURE_TOKEN, exchange_token=3, tradingsymbol="RELIANCE26JULFUT",
            name="RELIANCE", exchange="NFO", segment="NFO-FUT", instrument_type="FUT",
            expiry=expiry, lot_size=500, last_price=Decimal("2510"),
        ),
        Instrument(
            instrument_token=CALL_TOKEN, exchange_token=4, tradingsymbol="RELIANCE26JUL2500CE",
            name="RELIANCE", exchange="NFO", segment="NFO-OPT", instrument_type="CE",
            expiry=expiry, strike=Decimal("2500"), lot_size=500, last_price=Decimal("50"),
        ),
        Instrument(
            instrument_token=PUT_TOKEN, exchange_token=5, tradingsymbol="RELIANCE26JUL2500PE",
            name="RELIANCE", exchange="NFO", segment="NFO-OPT", instrument_type="PE",
            expiry=expiry, strike=Decimal("2500"), lot_size=500, last_price=Decimal("45"),
        ),
    ])
    db.commit()
    db.close()

    return {
        "equity": EQUITY_TOKEN,
        "equity_2": EQUITY_TOKEN_2,
        "future": FUTURE_TOKEN,
        "call": CALL_TOKEN,
        "put": PUT_TOKEN,
        "expiry": expiry,
    }
