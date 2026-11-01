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


def test_same_key_for_different_customers_creates_separate_events(client, db, make_customer):
    _, key_a = make_customer("Company A")
    _, key_b = make_customer("Company B")
    a = post_event(client, key_a, "order-1")
    b = post_event(client, key_b, "order-1")
    assert a.status_code == 201
    assert b.status_code == 201
    assert a.json()["event_id"] != b.json()["event_id"]
    assert count(db, "events") == 2


def test_event_type_without_subscription_creates_no_delivery(client, db, make_customer):
    _, key = make_customer(event_types=("invoice.paid",))
    r = post_event(client, key, "order-1")
    assert r.status_code == 201
    assert count(db, "events") == 1
    assert count(db, "deliveries") == 0


def test_revoked_key_is_rejected(client, db, make_customer):
    _, key = make_customer()
    db.execute("UPDATE api_keys SET revoked_at = now()")
    r = post_event(client, key, "order-1")
    assert r.status_code == 401
    assert count(db, "events") == 0


def test_events_only_fan_out_to_the_owners_endpoints(client, db, make_customer):
    _, key_a = make_customer("Company A")
    make_customer("Company B")
    post_event(client, key_a, "order-1")
    assert count(db, "deliveries") == 1
    same_owner = db.execute(
        """
        SELECT e.customer_id = p.customer_id
        FROM deliveries d
        JOIN events e ON e.id = d.event_id
        JOIN endpoints p ON p.id = d.endpoint_id
        """
    ).fetchone()[0]
    assert same_owner is True