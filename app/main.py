import hashlib
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from app.db import get_connection

app = FastAPI(title="Webhook Delivery Platform")
bearer = HTTPBearer(auto_error=False)


class EventIn(BaseModel):
    type: str
    payload: dict


def get_customer_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UUID:
    unauthorized = HTTPException(
        status_code=401,
        detail="invalid or missing API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT customer_id FROM api_keys WHERE key_hash = %s AND revoked_at IS NULL",
            (key_hash,),
        ).fetchone()
    if row is None:
        raise unauthorized
    return row[0]


@app.post("/events", status_code=201)
def create_event(
    event: EventIn,
    response: Response,
    idempotency_key: str = Header(...),
    customer_id: UUID = Depends(get_customer_id),
):
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO events (customer_id, idempotency_key, type, payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (customer_id, idempotency_key) DO NOTHING
            RETURNING id
            """,
            (customer_id, idempotency_key, event.type, Jsonb(event.payload)),
        ).fetchone()

        if row is None:
            existing = conn.execute(
                "SELECT id FROM events WHERE customer_id = %s AND idempotency_key = %s",
                (customer_id, idempotency_key),
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
            (event_id, customer_id, event.type),
        )

    return {"event_id": event_id, "duplicate": False}