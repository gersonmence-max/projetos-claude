-- ============================================================
--  stripe_migration.sql
--  Adiciona campos Stripe na tabela members
-- ============================================================

ALTER TABLE members
    ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT UNIQUE;

CREATE INDEX IF NOT EXISTS idx_members_stripe
    ON members (stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- Revoga acesso direto do frontend ao stripe_customer_id
-- (acessivel apenas via service key no backend)
COMMENT ON COLUMN members.stripe_customer_id IS
    'Apenas o backend com service key pode ler este campo';
