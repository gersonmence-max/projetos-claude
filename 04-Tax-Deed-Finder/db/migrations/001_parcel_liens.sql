-- Migration 001: Detailed liens table for Clerk's Office data
-- Run after schema.sql

CREATE TABLE IF NOT EXISTS parcel_liens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    -- Identification
    lien_id_external TEXT,          -- doc number from clerk portal
    lien_type TEXT NOT NULL,        -- irs_federal, state_tax, hoa, hospital,
                                    -- code_enforcement, judgment, mechanics, other
    -- Parties
    grantor TEXT,                   -- debtor (property owner)
    grantee TEXT,                   -- lienholder (IRS, HOA, contractor...)
    -- Financials
    lien_amount DECIMAL,
    -- Dates
    recorded_date DATE,
    -- Release
    is_released BOOLEAN DEFAULT false,
    release_doc_number TEXT,
    release_date DATE,
    -- Risk classification
    survives_tax_deed BOOLEAN NOT NULL DEFAULT false,
    survive_reason TEXT,            -- e.g. "IRS federal lien — 26 U.S.C. §7425"
    -- Metadata
    clerk_portal_url TEXT,
    source TEXT,                    -- portal name used
    raw_data JSONB DEFAULT '{}',
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_parcel_liens_parcel ON parcel_liens(parcel_id);
CREATE INDEX IF NOT EXISTS idx_parcel_liens_type ON parcel_liens(lien_type);
CREATE INDEX IF NOT EXISTS idx_parcel_liens_survives ON parcel_liens(survives_tax_deed);

-- View: summary of surviving liens per parcel (used by API and scoring)
CREATE OR REPLACE VIEW parcel_liens_summary AS
SELECT
    parcel_id,
    COUNT(*)                                            AS total_liens,
    COUNT(*) FILTER (WHERE NOT is_released)             AS active_liens,
    COUNT(*) FILTER (WHERE survives_tax_deed AND NOT is_released) AS surviving_liens,
    COALESCE(SUM(lien_amount) FILTER (WHERE NOT is_released), 0) AS total_active_amount,
    COALESCE(SUM(lien_amount) FILTER (WHERE survives_tax_deed AND NOT is_released), 0) AS surviving_amount,
    ARRAY_AGG(DISTINCT lien_type) FILTER (WHERE survives_tax_deed AND NOT is_released) AS surviving_types,
    MAX(checked_at)                                     AS last_checked
FROM parcel_liens
GROUP BY parcel_id;
