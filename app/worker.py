import random
import time

import httpx

from app.db import get_connection

MAX_RETRIES = 5
BASE_DELAY = 5        # seconds
MAX_DELAY = 3600      # one hour cap
POLL_INTERVAL = 1     # seconds to sleep when nothing is due

CLAIM_SQL = """
    SELECT d.id, d.event_id, d.retry_count, e.type, e.payload, p.url
    FROM deliveries d
    JOIN events e ON e.id = d.event_id
    JOIN endpoints p ON p.id = d.endpoint_id
    WHERE d.status = 'pending' AND d.next_attempt_at <= now()
    ORDER BY d.next_attempt_at
    LIMIT 1
    FOR UPDATE OF d SKIP LOCKED
"""


def backoff_seconds(retry_count: int) -> float:
    ceiling = min(MAX_DELAY, BASE_DELAY * 2 ** retry_count)
    return random.uniform(0, ceiling)  # full jitter


def process_one() -> bool:
    with get_connection() as conn:
        row = conn.execute(CLAIM_SQL).fetchone()
        if row is None:
            return False

        delivery_id, event_id, retry_count, event_type, payload, url = row

        status_code = None
        error = None
        started = time.monotonic()
        try:
            resp = httpx.post(
                url,
                json={"id": str(event_id), "type": event_type, "data": payload},
                headers={"Webhook-Id": str(event_id)},
                timeout=5.0,
            )
            status_code = resp.status_code
            ok = 200 <= status_code < 300
            if not ok:
                error = f"HTTP {status_code}"
        except httpx.HTTPError as exc:
            ok = False
            error = f"{type(exc).__name__}: {exc}"
        elapsed_ms = int((time.monotonic() - started) * 1000)

        conn.execute(
            """
            INSERT INTO delivery_attempts
                (delivery_id, status_code, response_time_ms, error)
            VALUES (%s, %s, %s, %s)
            """,
            (delivery_id, status_code, elapsed_ms, error),
        )

        if ok:
            conn.execute(
                "UPDATE deliveries SET status = 'succeeded' WHERE id = %s",
                (delivery_id,),
            )
            print(f"delivered {delivery_id}")
        elif retry_count + 1 >= MAX_RETRIES:
            conn.execute(
                "UPDATE deliveries SET status = 'dead', retry_count = retry_count + 1 WHERE id = %s",
                (delivery_id,),
            )
            print(f"gave up on {delivery_id}")
        else:
            delay = backoff_seconds(retry_count)
            conn.execute(
                """
                UPDATE deliveries
                SET retry_count = retry_count + 1,
                    next_attempt_at = now() + make_interval(secs => %s)
                WHERE id = %s
                """,
                (delay, delivery_id),
            )
            print(f"failed {delivery_id}, retrying in {delay:.1f}s")
        return True


def run():
    print("Worker started")
    while True:
        try:
            worked = process_one()
        except Exception as exc:
            print("worker error:", exc)
            worked = False
        if not worked:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()