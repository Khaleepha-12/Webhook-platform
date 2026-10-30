import hashlib
import secrets

from app.db import get_connection

DEMO_NAME = "Demo Co"
DEMO_URL = "http://receiver:9000/hook"
DEMO_SECRET = "demo-secret"  # must match SECRET in receiver.py


def main() -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM customers WHERE name = %s ORDER BY created_at LIMIT 1",
            (DEMO_NAME,),
        ).fetchone()
        if row is None:
            row = conn.execute(
                "INSERT INTO customers (name) VALUES (%s) RETURNING id",
                (DEMO_NAME,),
            ).fetchone()
        customer_id = row[0]

        has_endpoint = conn.execute(
            "SELECT 1 FROM endpoints WHERE customer_id = %s AND url = %s",
            (customer_id, DEMO_URL),
        ).fetchone()
        if has_endpoint is None:
            conn.execute(
                """
                INSERT INTO endpoints
                    (customer_id, url, signing_secret, subscribed_event_types)
                VALUES (%s, %s, %s, %s)
                """,
                (customer_id, DEMO_URL, DEMO_SECRET, ["payment.succeeded"]),
            )

        key = "whk_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        conn.execute(
            "INSERT INTO api_keys (customer_id, key_prefix, key_hash) VALUES (%s, %s, %s)",
            (customer_id, key[:8], key_hash),
        )

    print("Demo customer ready. API key (shown once, store it safely):")
    print(key)


if __name__ == "__main__":
    main()