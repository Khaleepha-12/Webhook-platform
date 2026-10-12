CREATE TABLE customers (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE events (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id      uuid NOT NULL REFERENCES customers(id),
  idempotency_key  text NOT NULL,
  type             text NOT NULL,
  payload          jsonb NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (customer_id, idempotency_key)
);

CREATE TABLE endpoints (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id             uuid NOT NULL REFERENCES customers(id),
  url                     text NOT NULL,
  signing_secret          text NOT NULL,
  is_active               boolean NOT NULL DEFAULT true,
  subscribed_event_types  text[] NOT NULL DEFAULT '{}',
  created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE deliveries (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id         uuid NOT NULL REFERENCES events(id),
  endpoint_id      uuid NOT NULL REFERENCES endpoints(id),
  status           text NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending', 'succeeded', 'dead')),
  retry_count      int NOT NULL DEFAULT 0,
  next_attempt_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (event_id, endpoint_id)
);

CREATE INDEX idx_deliveries_due
  ON deliveries (next_attempt_at)
  WHERE status = 'pending';

CREATE TABLE delivery_attempts (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id       uuid NOT NULL REFERENCES deliveries(id),
  attempted_at      timestamptz NOT NULL DEFAULT now(),
  status_code       int,
  response_time_ms  int,
  error             text
);
CREATE INDEX idx_attempts_delivery ON delivery_attempts (delivery_id);
CREATE INDEX idx_endpoints_customer ON endpoints (customer_id);