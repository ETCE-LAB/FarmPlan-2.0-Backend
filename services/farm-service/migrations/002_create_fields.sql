-- Independent Fields; legacy farms.data fields/templates are deliberately untouched.
CREATE TABLE IF NOT EXISTS fields (
    id UUID PRIMARY KEY,
    farm_id UUID NOT NULL REFERENCES farms(id) ON DELETE CASCADE,
    data JSONB NOT NULL CHECK (jsonb_typeof(data) = 'object')
);
CREATE INDEX IF NOT EXISTS fields_farm_id_idx ON fields(farm_id);
