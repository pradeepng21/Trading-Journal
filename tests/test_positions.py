from datetime import date, timedelta


def _trade(client, headers, token, txn, product, qty, price, trade_date=None):
    payload = {
        "instrument_token": token,
        "transaction_type": txn,
        "product": product,
        "quantity": qty,
        "price": str(price),
    }
    if trade_date:
        payload["trade_date"] = trade_date
    r = client.post("/trades/", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_all_position_endpoints_require_auth(client, seed_instruments):
    assert client.get("/positions").status_code == 401
    assert client.get("/holdings").status_code == 401
    assert client.post("/positions/eod-carry-forward").status_code == 401


def test_positions_empty_when_no_trades(client, auth_headers):
    r = client.get("/positions", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_holdings_empty_when_no_trades(client, auth_headers):
    r = client.get("/holdings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_mis_position_visible_same_day_and_not_carried(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "MIS", 20, "2490")
    _trade(client, auth_headers, seed_instruments["equity"], "SELL", "MIS", 10, "2495")

    positions = client.get("/positions", headers=auth_headers).json()
    assert len(positions) == 1
    assert positions[0]["product"] == "MIS"
    assert positions[0]["quantity"] == 10
    assert positions[0]["average_price"] == 2490.0

    r = client.post("/positions/eod-carry-forward", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"trades_carried": 0, "positions_updated": 0}

    # MIS never appears in holdings, ever
    assert client.get("/holdings", headers=auth_headers).json() == []


def test_cnc_position_flip_and_unrealized_pnl(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "CNC", 10, "2400")
    _trade(client, auth_headers, seed_instruments["equity"], "SELL", "CNC", 15, "2450")

    positions = client.get("/positions", headers=auth_headers).json()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["product"] == "CNC"
    assert pos["quantity"] == -5
    assert pos["average_price"] == 2450.0
    # seeded last_price for the equity is 2500: (2500 - 2450) * -5 = -250
    assert pos["unrealized_pnl"] == -250.0


def test_nrml_position(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["future"], "BUY", "NRML", 500, "2500")

    positions = client.get("/positions", headers=auth_headers).json()
    assert len(positions) == 1
    assert positions[0]["product"] == "NRML"
    assert positions[0]["quantity"] == 500


def test_eod_moves_cnc_into_holdings_and_is_idempotent(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "CNC", 10, "2400")

    assert client.get("/holdings", headers=auth_headers).json() == []

    r = client.post("/positions/eod-carry-forward", headers=auth_headers)
    assert r.json() == {"trades_carried": 1, "positions_updated": 1}

    holdings = client.get("/holdings", headers=auth_headers).json()
    assert len(holdings) == 1
    assert holdings[0]["quantity"] == 10
    assert holdings[0]["average_price"] == 2400.0

    # positions should still show the same CNC position, now sourced from the snapshot
    positions = client.get("/positions", headers=auth_headers).json()
    assert len(positions) == 1
    assert positions[0]["quantity"] == 10

    # running EOD again with nothing new is a no-op
    r = client.post("/positions/eod-carry-forward", headers=auth_headers)
    assert r.json() == {"trades_carried": 0, "positions_updated": 0}


def test_position_fully_closed_after_eod_disappears_from_both_views(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "CNC", 10, "2400")
    client.post("/positions/eod-carry-forward", headers=auth_headers)

    _trade(client, auth_headers, seed_instruments["equity"], "SELL", "CNC", 10, "2450")

    # visible as a position (uncarried sell against the carried snapshot) but net zero
    positions = client.get("/positions", headers=auth_headers).json()
    assert positions == []

    r = client.post("/positions/eod-carry-forward", headers=auth_headers)
    assert r.json()["trades_carried"] == 1

    assert client.get("/holdings", headers=auth_headers).json() == []
    assert client.get("/positions", headers=auth_headers).json() == []


def test_backdated_trade_visible_immediately_and_self_heals_on_eod(client, auth_headers, seed_instruments):
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "CNC", 10, "2400")
    _trade(client, auth_headers, seed_instruments["equity"], "SELL", "CNC", 15, "2450")
    client.post("/positions/eod-carry-forward", headers=auth_headers)

    # snapshot is now short 5 @ 2450; backdate a buy of 3 to before today
    backdated = (date.today() - timedelta(days=5)).isoformat()
    _trade(client, auth_headers, seed_instruments["equity"], "BUY", "CNC", 3, "2300", trade_date=backdated)

    positions = client.get("/positions", headers=auth_headers).json()
    assert len(positions) == 1
    assert positions[0]["quantity"] == -2  # visible immediately, before any further EOD run

    r = client.post("/positions/eod-carry-forward", headers=auth_headers)
    assert r.json() == {"trades_carried": 1, "positions_updated": 1}

    # full chronological refold: buy3@2300 (day-5) -> buy10@2400 (avg 2376.9231) -> sell15@2450 (flips) -> -2 @ 2450
    holdings = client.get("/holdings", headers=auth_headers).json()
    assert holdings[0]["quantity"] == -2
    assert holdings[0]["average_price"] == 2450.0


def test_positions_and_holdings_scoped_per_user(client, seed_instruments):
    client.post("/register", json={"username": "u1", "email": "u1@test.com", "password": "Secret123!"})
    client.post("/register", json={"username": "u2", "email": "u2@test.com", "password": "Secret123!"})
    token1 = client.post("/login", data={"username": "u1", "password": "Secret123!"}).json()["access_token"]
    token2 = client.post("/login", data={"username": "u2", "password": "Secret123!"}).json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    _trade(client, headers1, seed_instruments["equity"], "BUY", "CNC", 10, "2400")

    assert len(client.get("/positions", headers=headers1).json()) == 1
    assert client.get("/positions", headers=headers2).json() == []

    client.post("/positions/eod-carry-forward", headers=headers1)
    assert len(client.get("/holdings", headers=headers1).json()) == 1
    assert client.get("/holdings", headers=headers2).json() == []
