from app import worker


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def seed_delivery(db, make_customer, retry_count=0):
    customer_id, _ = make_customer()
    event_id = db.execute(
        """
        INSERT INTO events (customer_id, idempotency_key, type, payload)
        VALUES (%s, 'k1', 'payment.succeeded', '{}') RETURNING id
        """,
        (customer_id,),
    ).fetchone()[0]
    endpoint_id = db.execute(
        "SELECT id FROM endpoints WHERE customer_id = %s", (customer_id,)
    ).fetchone()[0]
    return db.execute(
        """
        INSERT INTO deliveries (event_id, endpoint_id, retry_count)
        VALUES (%s, %s, %s) RETURNING id
        """,
        (event_id, endpoint_id, retry_count),
    ).fetchone()[0]


def get_delivery(db, delivery_id):
    return db.execute(
        "SELECT status, retry_count FROM deliveries WHERE id = %s", (delivery_id,)
    ).fetchone()


def test_returns_false_when_nothing_is_due(db):
    assert worker.process_one() is False


def test_successful_delivery_is_marked_succeeded_and_logged(db, make_customer, monkeypatch):
    delivery_id = seed_delivery(db, make_customer)
    monkeypatch.setattr(worker.httpx, "post", lambda *a, **k: FakeResponse(200))

    assert worker.process_one() is True

    assert get_delivery(db, delivery_id) == ("succeeded", 0)
    code = db.execute(
        "SELECT status_code FROM delivery_attempts WHERE delivery_id = %s",
        (delivery_id,),
    ).fetchone()[0]
    assert code == 200


def test_failed_delivery_stays_pending_and_counts_a_retry(db, make_customer, monkeypatch):
    delivery_id = seed_delivery(db, make_customer)
    monkeypatch.setattr(worker.httpx, "post", lambda *a, **k: FakeResponse(503))

    worker.process_one()

    assert get_delivery(db, delivery_id) == ("pending", 1)
    error = db.execute(
        "SELECT error FROM delivery_attempts WHERE delivery_id = %s", (delivery_id,)
    ).fetchone()[0]
    assert error == "HTTP 503"


def test_delivery_becomes_dead_after_max_retries(db, make_customer, monkeypatch):
    delivery_id = seed_delivery(db, make_customer, retry_count=worker.MAX_RETRIES - 1)
    monkeypatch.setattr(worker.httpx, "post", lambda *a, **k: FakeResponse(500))

    worker.process_one()

    assert get_delivery(db, delivery_id) == ("dead", worker.MAX_RETRIES)