import hashlib
import secrets
from pathlib import Path
from urllib.parse import urlparse
import os

import psycopg
import pytest
from fastapi.testclient import TestClient

DB_URL = os.environ.get("DATABASE_URL", "")
DB_NAME = urlparse(DB_URL).path.lstrip("/")
SQL_DIR = Path(__file__).resolve().parent.parent / "db"
TABLES = "delivery_attempts, deliveries, api_keys, events, endpoints, customers"


@pytest.fixture(scope="session")
def _schema():
    if not DB_NAME.endswith("_test"):
        pytest.skip("DATABASE_URL must point to a database whose name ends in _test")
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
        for path in sorted(SQL_DIR.glob("*.sql")):
            conn.execute(path.read_text())


@pytest.fixture
def db(_schema):
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {TABLES} CASCADE")
        yield conn


@pytest.fixture
def client(db):
    from app.main import app

    return TestClient(app)


@pytest.fixture
def make_customer(db):
    def _make(name="Test Co", event_types=("payment.succeeded",), with_endpoint=True):
        customer_id = db.execute(
            "INSERT INTO customers (name) VALUES (%s) RETURNING id", (name,)
        ).fetchone()[0]
        key = "whk_" + secrets.token_urlsafe(16)
        db.execute(
            "INSERT INTO api_keys (customer_id, key_prefix, key_hash) VALUES (%s, %s, %s)",
            (customer_id, key[:8], hashlib.sha256(key.encode()).hexdigest()),
        )
        if with_endpoint:
            db.execute(
                """
                INSERT INTO endpoints
                    (customer_id, url, signing_secret, subscribed_event_types)
                VALUES (%s, %s, %s, %s)
                """,
                (customer_id, "http://example.test/hook", "secret", list(event_types)),
            )
        return customer_id, key

    return _make