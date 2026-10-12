CREATE TABLE api_keys (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id  uuid NOT NULL REFERENCES customers(id),
  key_prefix   text NOT NULL,
  key_hash     text NOT NULL UNIQUE,
  created_at   timestamptz NOT NULL DEFAULT now(),
  revoked_at   timestamptz
);

CREATE INDEX idx_api_keys_customer ON api_keys (customer_id);