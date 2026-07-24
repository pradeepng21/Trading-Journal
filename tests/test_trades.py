from datetime import date, timedelta


def test_create_and_list_trades_require_auth(client, seed_instruments):
    r = client.post("/trades/", json={
        "instrument_token": seed_instruments["equity"],
        "transaction_type": "BUY",
        "product": "CNC",
        "quantity": 10,
        "price": "2400",
    })
    assert r.status_code == 401

    r = client.get("/trades/")
    assert r.status_code == 401


def test_create_trade_success(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 10,
            "price": "2400.50",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["instrument_token"] == seed_instruments["equity"]
    assert body["transaction_type"] == "BUY"
    assert body["product"] == "CNC"
    assert body["quantity"] == 10
    assert body["price"] == 2400.50
    assert body["carried_forward"] is False
    assert body["trade_date"] == date.today().isoformat()


def test_create_trade_with_explicit_backdated_date(client, auth_headers, seed_instruments):
    backdated = (date.today() - timedelta(days=3)).isoformat()
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 5,
            "price": "2300",
            "trade_date": backdated,
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["trade_date"] == backdated


def test_create_trade_unknown_instrument_returns_404(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": 999999,
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 10,
            "price": "100",
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_create_trade_future_date_returns_422(client, auth_headers, seed_instruments):
    future = (date.today() + timedelta(days=1)).isoformat()
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 10,
            "price": "100",
            "trade_date": future,
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_trade_non_positive_quantity_returns_422(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 0,
            "price": "100",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_trade_non_positive_price_returns_422(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "CNC",
            "quantity": 10,
            "price": "-5",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_trade_invalid_transaction_type_returns_422(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "HOLD",
            "product": "CNC",
            "quantity": 10,
            "price": "100",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_trade_invalid_product_returns_422(client, auth_headers, seed_instruments):
    r = client.post(
        "/trades/",
        json={
            "instrument_token": seed_instruments["equity"],
            "transaction_type": "BUY",
            "product": "FUTSWING",
            "quantity": 10,
            "price": "100",
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_list_trades_returns_only_current_users_trades(client, seed_instruments):
    client.post("/register", json={"username": "u1", "email": "u1@test.com", "password": "Secret123!"})
    client.post("/register", json={"username": "u2", "email": "u2@test.com", "password": "Secret123!"})

    token1 = client.post("/login", data={"username": "u1", "password": "Secret123!"}).json()["access_token"]
    token2 = client.post("/login", data={"username": "u2", "password": "Secret123!"}).json()["access_token"]

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    client.post("/trades/", json={
        "instrument_token": seed_instruments["equity"], "transaction_type": "BUY",
        "product": "CNC", "quantity": 10, "price": "2400",
    }, headers=headers1)
    client.post("/trades/", json={
        "instrument_token": seed_instruments["equity"], "transaction_type": "BUY",
        "product": "CNC", "quantity": 20, "price": "2400",
    }, headers=headers2)

    r1 = client.get("/trades/", headers=headers1)
    r2 = client.get("/trades/", headers=headers2)

    assert len(r1.json()) == 1
    assert r1.json()[0]["quantity"] == 10
    assert len(r2.json()) == 1
    assert r2.json()[0]["quantity"] == 20


def test_list_trades_filters(client, auth_headers, seed_instruments):
    client.post("/trades/", json={
        "instrument_token": seed_instruments["equity"], "transaction_type": "BUY",
        "product": "CNC", "quantity": 10, "price": "2400",
    }, headers=auth_headers)
    client.post("/trades/", json={
        "instrument_token": seed_instruments["future"], "transaction_type": "BUY",
        "product": "NRML", "quantity": 500, "price": "2500",
    }, headers=auth_headers)

    r = client.get(
        f"/trades/?instrument_token={seed_instruments['equity']}", headers=auth_headers
    )
    assert len(r.json()) == 1
    assert r.json()[0]["instrument_token"] == seed_instruments["equity"]

    r = client.get("/trades/?product=NRML", headers=auth_headers)
    assert len(r.json()) == 1
    assert r.json()[0]["product"] == "NRML"

    r = client.get("/trades/", headers=auth_headers)
    assert len(r.json()) == 2
