-- ============================================================
--  schema.sql — Clube USA
--  Seguranca de nivel senior
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
--  whatsapp_groups — precisa existir antes de members
-- ============================================================
CREATE TABLE whatsapp_groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id_zapi   TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    language        VARCHAR(2) NOT NULL DEFAULT 'pt',
    capacity        INTEGER NOT NULL DEFAULT 1024,
    member_count    INTEGER NOT NULL DEFAULT 0,
    is_full         BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    invite_link     TEXT,
    sequence_number INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_groups_active   ON whatsapp_groups (is_active, is_full);
CREATE INDEX idx_groups_language ON whatsapp_groups (language);

-- ============================================================
--  members
--  PII criptografado — phone/email/name nunca em texto puro
-- ============================================================
CREATE TABLE members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_hash      TEXT NOT NULL UNIQUE,
    phone_enc       TEXT NOT NULL,
    email_hash      TEXT UNIQUE,
    email_enc       TEXT,
    name_enc        TEXT,
    language        VARCHAR(2)  NOT NULL DEFAULT 'pt' CHECK (language IN ('pt','es')),
    state           VARCHAR(50),
    plan            VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (plan IN ('free','vip')),
    status          VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','banned')),
    points          INTEGER NOT NULL DEFAULT 100,
    total_clicks    INTEGER NOT NULL DEFAULT 0,
    total_purchases INTEGER NOT NULL DEFAULT 0,
    level           VARCHAR(20) NOT NULL DEFAULT 'bronze',
    referral_code   VARCHAR(12) NOT NULL UNIQUE DEFAULT upper(substr(md5(random()::text), 1, 8)),
    referred_by     UUID REFERENCES members(id) ON DELETE SET NULL,
    referral_count  INTEGER NOT NULL DEFAULT 0,
    categories      TEXT[] NOT NULL DEFAULT ARRAY['all'],
    group_id        UUID REFERENCES whatsapp_groups(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    vip_started_at  TIMESTAMPTZ,
    vip_expires_at  TIMESTAMPTZ,
    vip_trial_used  BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_members_phone_hash ON members (phone_hash);
CREATE INDEX idx_members_email_hash ON members (email_hash);
CREATE INDEX idx_members_referral   ON members (referral_code);
CREATE INDEX idx_members_plan       ON members (plan);
CREATE INDEX idx_members_group      ON members (group_id);
CREATE INDEX idx_members_active     ON members (status) WHERE deleted_at IS NULL;

-- ============================================================
--  deals — dados publicos, sem PII
-- ============================================================
CREATE TABLE deals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asin            VARCHAR(20) NOT NULL,
    title           TEXT NOT NULL,
    price_now       NUMERIC(10,2) NOT NULL,
    price_was       NUMERIC(10,2),
    discount_pct    SMALLINT NOT NULL,
    rating          NUMERIC(3,1),
    reviews         INTEGER,
    score           NUMERIC(5,1) NOT NULL DEFAULT 0,
    score_label     VARCHAR(20),
    price_context   TEXT,
    image_url       TEXT,
    affiliate_url   TEXT NOT NULL,
    category        VARCHAR(50),
    source          VARCHAR(20) NOT NULL DEFAULT 'amazon',
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','rejected','sent')),
    auto_approved   BOOLEAN NOT NULL DEFAULT FALSE,
    language        VARCHAR(2) NOT NULL DEFAULT 'pt',
    slot            VARCHAR(20),
    sent_at         TIMESTAMPTZ,
    found_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_deals_status   ON deals (status);
CREATE INDEX idx_deals_score    ON deals (score DESC);
CREATE INDEX idx_deals_category ON deals (category);
CREATE INDEX idx_deals_asin     ON deals (asin);

-- ============================================================
--  clicks — rastreamento com UTM unico por membro+deal
-- ============================================================
CREATE TABLE clicks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    member_id   UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    deal_id     UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    utm_code    VARCHAR(32) NOT NULL UNIQUE,
    clicked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_hash     TEXT,
    converted   BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_clicks_member ON clicks (member_id);
CREATE INDEX idx_clicks_deal   ON clicks (deal_id);
CREATE INDEX idx_clicks_week   ON clicks (clicked_at)
    WHERE clicked_at > NOW() - INTERVAL '7 days';

-- ============================================================
--  referrals — programa de indicacao
-- ============================================================
CREATE TABLE referrals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referrer_id     UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    referred_id     UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    points_awarded  INTEGER NOT NULL DEFAULT 200,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','confirmed','rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at    TIMESTAMPTZ,
    UNIQUE (referrer_id, referred_id)
);
CREATE INDEX idx_referrals_referrer ON referrals (referrer_id);

-- ============================================================
--  raffles — sorteios
-- ============================================================
CREATE TABLE raffles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    week_start  DATE NOT NULL UNIQUE,
    prize_usd   NUMERIC(8,2) NOT NULL,
    prize_type  VARCHAR(50) NOT NULL DEFAULT 'amazon_gift_card',
    plan        VARCHAR(20) NOT NULL DEFAULT 'free',
    status      VARCHAR(20) NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','closed','drawn')),
    winner_id   UUID REFERENCES members(id) ON DELETE SET NULL,
    drawn_at    TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
--  audit_logs — IMUTAVEL, append-only
-- ============================================================
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    actor_id    UUID,
    actor_type  VARCHAR(20) NOT NULL DEFAULT 'system'
                CHECK (actor_type IN ('member','admin','system')),
    action      VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id   UUID,
    ip_hash     TEXT,
    user_agent  TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_actor  ON audit_logs (actor_id);
CREATE INDEX idx_audit_action ON audit_logs (action);
CREATE INDEX idx_audit_time   ON audit_logs (created_at DESC);
REVOKE DELETE, UPDATE, TRUNCATE ON audit_logs FROM PUBLIC;

-- ============================================================
--  TRIGGERS
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_members_updated
    BEFORE UPDATE ON members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_groups_updated
    BEFORE UPDATE ON whatsapp_groups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE FUNCTION update_member_level()
RETURNS TRIGGER AS $$
BEGIN
    NEW.level = CASE
        WHEN NEW.points >= 5000 THEN 'vip'
        WHEN NEW.points >= 2000 THEN 'gold'
        WHEN NEW.points >= 500  THEN 'silver'
        ELSE 'bronze'
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_member_level
    BEFORE UPDATE OF points ON members
    FOR EACH ROW EXECUTE FUNCTION update_member_level();

CREATE OR REPLACE FUNCTION sync_group_capacity()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.group_id IS NOT NULL THEN
        UPDATE whatsapp_groups
        SET member_count = member_count + 1,
            is_full = (member_count + 1 >= capacity)
        WHERE id = NEW.group_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_capacity
    AFTER INSERT ON members
    FOR EACH ROW EXECUTE FUNCTION sync_group_capacity();

-- ============================================================
--  ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE members   ENABLE ROW LEVEL SECURITY;
ALTER TABLE clicks    ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;

CREATE POLICY member_select_own ON members
    FOR SELECT USING (id = auth.uid());

CREATE POLICY member_update_own ON members
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (
        plan = (SELECT plan FROM members WHERE id = auth.uid()) AND
        status = (SELECT status FROM members WHERE id = auth.uid())
    );

CREATE POLICY clicks_own ON clicks
    FOR SELECT USING (member_id = auth.uid());

CREATE POLICY referrals_own ON referrals
    FOR SELECT USING (referrer_id = auth.uid());

CREATE POLICY deals_public ON deals
    FOR SELECT USING (status IN ('approved','sent'));
