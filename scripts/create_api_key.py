import hashlib
import secrets
import sys

from app.db import get_connection


def main(customer_id: str) -> None:
    key = "whk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO api_keys (customer_id, key_prefix, key_hash) VALUES (%s, %s, %s)",
            (customer_id, key[:8], key_hash),
        )
    print("API key (shown once, store it safely):")
    print(key)


if __name__ == "__main__":
    main(sys.argv[1])