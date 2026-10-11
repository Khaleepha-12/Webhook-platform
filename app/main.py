from uuid import UUID

from fastapi import FastAPI, Header, Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.db import get_connection

app = FastAPI(title="Webhook Delivery Platform")


class EventIn(BaseModel):
    type: str
    payload: dict


@app.post("/events", status_code=201)
def create_event(
    event: EventIn,
    response: Response,
    idempotency_key: str = Header(...),
    x_customer_id: UUID = Header(...),
):
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO events (customer_id, idempotency_key, type, payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (customer_id, idempotency_key) DO NOTHING
            RETURNING id
            """,
            (x_customer_id, idempotency_key, event.type, Jsonb(event.payload)),
        ).fetchone()

        if row is None:
            existing = conn.execute(
                "SELECT id FROM events WHERE customer_id = %s AND idempotency_key = %s",
                (x_customer_id, idempotency_key),
            ).fetchone()
            response.status_code = 200
            return {"event_id": existing[0], "duplicate": True}

        event_id = row[0]
        conn.execute(
            """
            INSERT INTO deliveries (event_id, endpoint_id)
            SELECT %s, id FROM endpoints
            WHERE customer_id = %s
              AND is_active
              AND %s = ANY(subscribed_event_types)
            """,
            (event_id, x_customer_id, event.type),
        )

    return {"event_id": event_id, "duplicate": False}