# Trading Journal

A FastAPI backend for logging trades, tracking intraday/carry-forward positions and holdings, and browsing NSE/NFO instruments synced from Kite. Built with SQLAlchemy (MySQL) and JWT-based auth.

## Features

- **Auth** — user registration and login with bcrypt password hashing and JWT access tokens.
- **Instruments** — searchable catalog of equities, futures and options (option chains by underlying/expiry), auto-synced daily from the [Kite instruments](https://api.kite.trade/instruments) feed on app startup.
- **Trades** — log buy/sell trades (MIS/CNC/NRML) and list/filter them by instrument, product or date range.
- **Positions & Holdings** — computed intraday positions, carry-forward holdings, and an end-of-day carry-forward routine that rolls open MIS/NRML positions into the next day.

## Tech stack

- FastAPI + Uvicorn
- SQLAlchemy ORM + MySQL (`pymysql`)
- `python-jose` (JWT) + `passlib[bcrypt]` for auth
- `pandas` / `requests` for the Kite instrument sync
- `loguru` for logging
- `pytest` + `httpx` TestClient for tests (SQLite in-memory)

## Project structure

```
config/      # app config, logging setup
db_ops/      # SQLAlchemy engine/session setup
models/      # ORM models (User, Instrument, Trade, CarryforwardPosition, AppMetadata)
schemas/     # Pydantic request/response schemas
routers/     # FastAPI routers (users, instruments, trades, positions)
utils/       # auth, security deps, and service layer (trade/position/instrument logic, startup sync)
tests/       # pytest suite
main.py      # app entrypoint
```

## Setup

1. Install dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy pymysql python-jose[cryptography] passlib[bcrypt] pandas requests loguru pytz pydantic[email]
   ```
2. Create a MySQL database and update `DATABASE_URL` and `SECRET_KEY` in [config/config.py](config/config.py) for your environment.
3. Run the API:
   ```bash
   python main.py
   ```
   The server starts on `http://0.0.0.0:8000` and kicks off a background sync of the day's Kite instruments.

## Running tests

```bash
pytest
```

Tests spin up an isolated in-memory SQLite database per test and never touch the configured MySQL instance.

## API overview

| Area        | Endpoints |
|-------------|-----------|
| Auth        | `POST /register`, `POST /login`, `GET /me` |
| Instruments | `GET /instruments/`, `/search`, `/equities`, `/underlyings`, `/options/{underlying}[/expiries\|/chain]`, `/futures/{underlying}[/expiries]`, `/{instrument_token}` |
| Trades      | `POST /trades/`, `GET /trades/` |
| Positions   | `GET /positions`, `GET /holdings`, `POST /positions/eod-carry-forward` |

All routes except `/register` and `/login` require a `Bearer` JWT obtained from `/login`.
