CREATE TABLE IF NOT EXISTS farms (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS farms_owner_created_idx ON farms (owner_id, created_at DESC);
