def test_all_instrument_endpoints_require_auth(client, seed_instruments):
    endpoints = [
        "/instruments/",
        "/instruments/search",
        "/instruments/equities",
        "/instruments/underlyings",
        f"/instruments/options/RELIANCE/expiries",
        f"/instruments/options/RELIANCE",
        f"/instruments/futures/RELIANCE/expiries",
        f"/instruments/futures/RELIANCE",
        f"/instruments/{seed_instruments['equity']}",
    ]

    for path in endpoints:
        r = client.get(path)
        assert r.status_code == 401, f"expected 401 for {path}, got {r.status_code}"


def test_get_all(client, auth_headers, seed_instruments):
    r = client.get("/instruments/", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_get_all_pagination(client, auth_headers, seed_instruments):
    r = client.get("/instruments/?skip=0&limit=2", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_instrument_by_token(client, auth_headers, seed_instruments):
    r = client.get(f"/instruments/{seed_instruments['equity']}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["tradingsymbol"] == "RELIANCE"


def test_get_instrument_not_found(client, auth_headers, seed_instruments):
    r = client.get("/instruments/999999", headers=auth_headers)
    assert r.status_code == 404


def test_search_is_reachable_and_not_shadowed(client, auth_headers, seed_instruments):
    # regression check: "/search" must not be swallowed by "/{instrument_token}"
    r = client.get("/instruments/search", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_search_by_symbol(client, auth_headers, seed_instruments):
    r = client.get("/instruments/search?symbol=RELI", headers=auth_headers)
    assert r.status_code == 200
    symbols = {i["tradingsymbol"] for i in r.json()}
    assert "RELIANCE" in symbols
    assert "INFY" not in symbols


def test_search_by_exchange_and_segment(client, auth_headers, seed_instruments):
    r = client.get("/instruments/search?exchange=NFO&segment=NFO-FUT", headers=auth_headers)
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["tradingsymbol"] == "RELIANCE26JULFUT"


def test_equities_excludes_derivatives(client, auth_headers, seed_instruments):
    r = client.get("/instruments/equities", headers=auth_headers)
    assert r.status_code == 200
    symbols = {i["tradingsymbol"] for i in r.json()}
    assert symbols == {"RELIANCE", "INFY"}


def test_equities_symbol_filter(client, auth_headers, seed_instruments):
    r = client.get("/instruments/equities?symbol=INFY", headers=auth_headers)
    assert r.status_code == 200
    results = r.json()
    assert len(results) == 1
    assert results[0]["tradingsymbol"] == "INFY"


def test_underlyings_default_includes_both_derivative_types(client, auth_headers, seed_instruments):
    r = client.get("/instruments/underlyings", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == ["RELIANCE"]


def test_underlyings_filtered_by_derivative_type(client, auth_headers, seed_instruments):
    r = client.get("/instruments/underlyings?derivative_type=futures", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == ["RELIANCE"]

    r = client.get("/instruments/underlyings?derivative_type=options", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == ["RELIANCE"]


def test_underlyings_rejects_invalid_derivative_type(client, auth_headers, seed_instruments):
    r = client.get("/instruments/underlyings?derivative_type=bogus", headers=auth_headers)
    assert r.status_code == 422


def test_future_expiries(client, auth_headers, seed_instruments):
    r = client.get("/instruments/futures/RELIANCE/expiries", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == [seed_instruments["expiry"].isoformat()]


def test_futures_all_and_by_expiry(client, auth_headers, seed_instruments):
    r = client.get("/instruments/futures/RELIANCE", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(
        f"/instruments/futures/RELIANCE?expiry={seed_instruments['expiry'].isoformat()}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get("/instruments/futures/RELIANCE?expiry=2099-01-01", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_futures_unknown_underlying_returns_empty_list(client, auth_headers, seed_instruments):
    r = client.get("/instruments/futures/NOSUCHSTOCK", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_option_expiries(client, auth_headers, seed_instruments):
    r = client.get("/instruments/options/RELIANCE/expiries", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == [seed_instruments["expiry"].isoformat()]


def test_option_chain(client, auth_headers, seed_instruments):
    r = client.get(
        f"/instruments/options/RELIANCE/chain?expiry={seed_instruments['expiry'].isoformat()}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["strike"] == 2500.0
    assert rows[0]["call"]["tradingsymbol"] == "RELIANCE26JUL2500CE"
    assert rows[0]["put"]["tradingsymbol"] == "RELIANCE26JUL2500PE"


def test_option_chain_requires_expiry(client, auth_headers, seed_instruments):
    r = client.get("/instruments/options/RELIANCE/chain", headers=auth_headers)
    assert r.status_code == 422


def test_options_all_for_underlying(client, auth_headers, seed_instruments):
    r = client.get("/instruments/options/RELIANCE", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 2
