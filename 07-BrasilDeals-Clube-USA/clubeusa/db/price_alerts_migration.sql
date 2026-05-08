-- price_alerts_migration.sql
-- Executar no Supabase SQL Editor

CREATE TABLE price_alerts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id     UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    asin          VARCHAR(20) NOT NULL,
    product_title TEXT,
    price_current NUMERIC(10,2),
    target_type   VARCHAR(10) NOT NULL CHECK (target_type IN ('price', 'percent')),
    target_value  NUMERIC(10,2) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active', 'triggered', 'cancelled')),
    triggered_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_member ON price_alerts (member_id);
CREATE INDEX idx_alerts_active ON price_alerts (status) WHERE status = 'active';
CREATE INDEX idx_alerts_asin   ON price_alerts (asin);

ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY alerts_own_select ON price_alerts
    FOR SELECT USING (member_id = auth.uid());

CREATE POLICY alerts_own_insert ON price_alerts
    FOR INSERT WITH CHECK (member_id = auth.uid());

CREATE POLICY alerts_own_update ON price_alerts
    FOR UPDATE USING (member_id = auth.uid());
