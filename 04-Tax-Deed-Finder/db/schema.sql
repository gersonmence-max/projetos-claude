-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Counties configuration
CREATE TABLE IF NOT EXISTS counties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    assessor_url TEXT,
    auction_platform TEXT NOT NULL, -- bid4assets, govease, realauction, direct
    auction_platform_county_id TEXT,
    assessor_api_type TEXT DEFAULT 'scrape', -- rest, scrape, csv
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Parcels collected
CREATE TABLE IF NOT EXISTS parcels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    parcel_number TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    property_type TEXT DEFAULT 'land', -- land, house, commercial, other
    acres DECIMAL,
    sqft INTEGER,
    bedrooms INTEGER,
    bathrooms DECIMAL,
    year_built INTEGER,
    zoning TEXT,
    gps_lat DECIMAL,
    gps_lng DECIMAL,
    auction_platform TEXT,
    auction_url TEXT,
    minimum_bid DECIMAL,
    auction_date DATE,
    auction_status TEXT DEFAULT 'upcoming', -- upcoming, active, sold, cancelled
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(county_id, external_id)
);

-- Parcel risk data
CREATE TABLE IF NOT EXISTS parcel_risks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    flood_zone TEXT DEFAULT 'X',
    flood_zone_source TEXT,
    wetlands_percent DECIMAL DEFAULT 0,
    wetlands_source TEXT,
    tornado_risk TEXT DEFAULT 'low', -- low, medium, high
    tornado_f2_count_10yr INTEGER DEFAULT 0,
    slope_percent DECIMAL DEFAULT 0,
    has_road_access BOOLEAN DEFAULT true,
    road_type TEXT DEFAULT 'paved', -- paved, unpaved, none
    nearest_city TEXT,
    nearest_city_distance_miles DECIMAL,
    nearest_city_population INTEGER,
    drive_time_minutes DECIMAL,
    has_additional_liens BOOLEAN DEFAULT false,
    liens_amount DECIMAL DEFAULT 0,
    is_landlocked BOOLEAN DEFAULT false,
    passes_auto_filters BOOLEAN DEFAULT false,
    filter_fail_reasons TEXT[] DEFAULT '{}',
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Parcel valuations
CREATE TABLE IF NOT EXISTS parcel_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    assessed_value DECIMAL,
    market_value_estimate DECIMAL,
    price_per_acre DECIMAL,
    comparable_sales JSONB DEFAULT '[]',
    valuation_source TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- County demographics
CREATE TABLE IF NOT EXISTS county_demographics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    county_id UUID REFERENCES counties(id) ON DELETE CASCADE,
    population_2020 INTEGER,
    population_2023 INTEGER,
    population_latest INTEGER,
    growth_rate_3yr DECIMAL,
    growth_rate_1yr DECIMAL,
    median_household_income INTEGER,
    unemployment_rate DECIMAL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Parcel scores and analysis
CREATE TABLE IF NOT EXISTS parcel_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    score_total INTEGER DEFAULT 0,
    score_discount INTEGER DEFAULT 0,
    score_population_growth INTEGER DEFAULT 0,
    score_road_access INTEGER DEFAULT 0,
    score_size INTEGER DEFAULT 0,
    score_bid_price INTEGER DEFAULT 0,
    minimum_bid DECIMAL,
    market_value_estimate DECIMAL,
    discount_percent DECIMAL,
    of_resale_price DECIMAL,
    of_down_payment DECIMAL,
    of_monthly_payment DECIMAL,
    of_term_months INTEGER,
    of_total_return DECIMAL,
    of_roi_percent DECIMAL,
    of_months_to_recover DECIMAL,
    ai_analysis TEXT,
    ai_recommendation TEXT, -- comprar, monitorar, ignorar
    ai_analyzed_at TIMESTAMP WITH TIME ZONE,
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alerts sent
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL, -- new_opportunity, auction_tomorrow, price_drop
    score_at_alert INTEGER,
    email_sent_to TEXT,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Saved parcels
CREATE TABLE IF NOT EXISTS saved_parcels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parcel_id UUID REFERENCES parcels(id) ON DELETE CASCADE,
    notes TEXT,
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_parcels_county ON parcels(county_id);
CREATE INDEX IF NOT EXISTS idx_parcels_auction_date ON parcels(auction_date);
CREATE INDEX IF NOT EXISTS idx_parcels_auction_status ON parcels(auction_status);
CREATE INDEX IF NOT EXISTS idx_parcel_risks_passes ON parcel_risks(passes_auto_filters);
CREATE INDEX IF NOT EXISTS idx_parcel_scores_total ON parcel_scores(score_total);
CREATE INDEX IF NOT EXISTS idx_parcel_scores_parcel ON parcel_scores(parcel_id);
CREATE INDEX IF NOT EXISTS idx_counties_active ON counties(active);
CREATE INDEX IF NOT EXISTS idx_parcels_state ON parcels(state);
CREATE INDEX IF NOT EXISTS idx_parcels_property_type ON parcels(property_type);
