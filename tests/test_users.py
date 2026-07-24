def test_register_success(client):
    r = client.post(
        "/register",
        json={"username": "alice", "email": "alice@test.com", "password": "Secret123!"},
    )
    assert r.status_code == 200
    assert r.json() == {"message": "Registration Successful"}


def test_register_duplicate_username_returns_400(client, register_user):
    register_user(username="alice", email="alice@test.com")
    r = register_user(username="alice", email="different@test.com")
    assert r.status_code == 400


def test_register_duplicate_email_returns_400(client, register_user):
    register_user(username="alice", email="alice@test.com")
    r = register_user(username="different", email="alice@test.com")
    assert r.status_code == 400


def test_register_invalid_email_returns_422(client):
    r = client.post(
        "/register",
        json={"username": "alice", "email": "not-an-email", "password": "Secret123!"},
    )
    assert r.status_code == 422


def test_login_success(client, register_user):
    register_user(username="bob", email="bob@test.com")
    r = client.post("/login", data={"username": "bob", "password": "Secret123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_unknown_username_returns_401(client):
    r = client.post("/login", data={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401


def test_login_wrong_password_returns_401(client, register_user):
    register_user(username="carol", email="carol@test.com")
    r = client.post("/login", data={"username": "carol", "password": "wrong-password"})
    assert r.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    r = client.get("/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "trader"
    assert body["email"] == "trader@test.com"
    assert "id" in body


def test_me_without_token_returns_401(client):
    r = client.get("/me")
    assert r.status_code == 401


def test_me_with_garbage_token_returns_401(client):
    r = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
