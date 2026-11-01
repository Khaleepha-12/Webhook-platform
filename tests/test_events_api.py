def post_event(client, key, idem, body=None):
    return client.post(
        "/events",
        json=body or {"type": "payment.succeeded", "payload": {"amount": 5000}},
        headers={"Authorization": f"Bearer {key}", "Idempotency-Key": idem},
    )


def count(db, table):
    return db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_new_event_creates_event_and_pending_delivery(client, db, make_customer):
    _, key = make_customer()
    r = post_event(client, key, "order-1")
    assert r.status_code == 201
    assert r.json()["duplicate"] is False
    assert count(db, "events") == 1
    assert count(db, "deliveries") == 1
    assert db.execute("SELECT status FROM deliveries").fetchone()[0] == "pending"


def test_duplicate_key_returns_original_and_creates_nothing_new(client, db, make_customer):
    _, key = make_customer()
    first = post_event(client, key, "order-1")
    second = post_event(client, key, "order-1")
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["event_id"] == first.json()["event_id"]
    assert count(db, "events") == 1
    assert count(db, "deliveries") == 1


def test_missing_api_key_is_rejected(client, db):
    r = client.post(
        "/events",
        json={"type": "payment.succeeded", "payload": {}},
        headers={"Idempotency-Key": "order-1"},
    )
    assert r.status_code == 401
    assert count(db, "events") == 0