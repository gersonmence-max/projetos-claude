-- Seed 50 counties for Phase 2 monitoring
-- auction_platform: bid4assets, govease, realauction, direct

INSERT INTO counties (name, state, assessor_url, auction_platform, auction_platform_county_id, assessor_api_type, active) VALUES

-- Texas (15 counties) — mostly bid4assets / realauction
('Kaufman', 'TX', 'https://www.kaufmancad.org', 'bid4assets', 'kaufman-tx', 'scrape', true),
('Montgomery', 'TX', 'https://www.mcad-tx.org', 'bid4assets', 'montgomery-tx', 'scrape', true),
('Bastrop', 'TX', 'https://www.bastropcad.org', 'realauction', 'bastrop-tx', 'scrape', true),
('Caldwell', 'TX', 'https://www.caldwellcad.org', 'realauction', 'caldwell-tx', 'scrape', true),
('Ellis', 'TX', 'https://www.elliscad.com', 'bid4assets', 'ellis-tx', 'scrape', true),
('Rockwall', 'TX', 'https://www.rockwallcad.com', 'bid4assets', 'rockwall-tx', 'scrape', true),
('Hays', 'TX', 'https://www.hayscad.com', 'realauction', 'hays-tx', 'scrape', true),
('Comal', 'TX', 'https://www.comalcad.org', 'realauction', 'comal-tx', 'scrape', true),
('Liberty', 'TX', 'https://www.libertycad.org', 'bid4assets', 'liberty-tx', 'scrape', true),
('Chambers', 'TX', 'https://www.chamberscad.org', 'bid4assets', 'chambers-tx', 'scrape', true),
('Denton', 'TX', 'https://www.dentoncad.com', 'bid4assets', 'denton-tx', 'scrape', true),
('Fort Bend', 'TX', 'https://www.fbcad.org', 'realauction', 'fortbend-tx', 'scrape', true),
('Guadalupe', 'TX', 'https://www.guadalupecad.org', 'realauction', 'guadalupe-tx', 'scrape', true),
('Wilson', 'TX', 'https://www.wilsoncad.org', 'realauction', 'wilson-tx', 'scrape', true),
('Collin', 'TX', 'https://www.collincad.org', 'bid4assets', 'collin-tx', 'scrape', true),

-- Georgia (11 counties) — govease
('Dawson', 'GA', 'https://www.qpublic.net/ga/dawson', 'govease', 'dawson-ga', 'scrape', true),
('Jackson', 'GA', 'https://www.qpublic.net/ga/jackson', 'govease', 'jackson-ga', 'scrape', true),
('Pickens', 'GA', 'https://www.qpublic.net/ga/pickens', 'govease', 'pickens-ga', 'scrape', true),
('Cherokee', 'GA', 'https://www.cherokeega.com/assessors', 'govease', 'cherokee-ga', 'scrape', true),
('Forsyth', 'GA', 'https://www.forsythco.com/assessors', 'govease', 'forsyth-ga', 'scrape', true),
('Barrow', 'GA', 'https://www.qpublic.net/ga/barrow', 'govease', 'barrow-ga', 'scrape', true),
('Walton', 'GA', 'https://www.qpublic.net/ga/walton', 'govease', 'walton-ga', 'scrape', true),
('Hall', 'GA', 'https://www.hallcounty.org/assessors', 'govease', 'hall-ga', 'scrape', true),
('Henry', 'GA', 'https://www.qpublic.net/ga/henry', 'govease', 'henry-ga', 'scrape', true),
('Paulding', 'GA', 'https://www.pauldingcountyga.gov/assessors', 'govease', 'paulding-ga', 'scrape', true),
('Newton', 'GA', 'https://www.qpublic.net/ga/newton', 'govease', 'newton-ga', 'scrape', true),

-- Tennessee (4 counties) — realauction
('Rutherford', 'TN', 'https://www.rutherfordcountytn.gov/assessor', 'realauction', 'rutherford-tn', 'scrape', true),
('Williamson', 'TN', 'https://www.williamsontn.gov/assessor', 'realauction', 'williamson-tn', 'scrape', true),
('Wilson', 'TN', 'https://www.wilsoncountytn.gov/assessor', 'realauction', 'wilson-tn', 'scrape', true),
('Maury', 'TN', 'https://www.maurycounty-tn.gov/assessor', 'realauction', 'maury-tn', 'scrape', true),

-- Arkansas (4 counties) — bid4assets
('Benton', 'AR', 'https://www.bentoncountyar.gov/assessor', 'bid4assets', 'benton-ar', 'scrape', true),
('Washington', 'AR', 'https://www.washingtoncoar.gov/assessor', 'bid4assets', 'washington-ar', 'scrape', true),
('Saline', 'AR', 'https://www.salinecountyar.gov/assessor', 'bid4assets', 'saline-ar', 'scrape', true),
('Faulkner', 'AR', 'https://www.faulknercountyar.gov/assessor', 'bid4assets', 'faulkner-ar', 'scrape', true),

-- Florida (10 counties) — realauction
('Polk', 'FL', 'https://www.polkpa.org', 'realauction', 'polk-fl', 'scrape', true),
('Pasco', 'FL', 'https://www.pascopa.com', 'realauction', 'pasco-fl', 'scrape', true),
('Hernando', 'FL', 'https://www.hernandopa-fl.us', 'realauction', 'hernando-fl', 'scrape', true),
('Volusia', 'FL', 'https://www.vcpa.us', 'realauction', 'volusia-fl', 'scrape', true),
('Marion', 'FL', 'https://www.pa.marion.fl.us', 'realauction', 'marion-fl', 'scrape', true),
('St. Johns', 'FL', 'https://www.sjcpa.us', 'realauction', 'stjohns-fl', 'scrape', true),
('Flagler', 'FL', 'https://www.flaglerpa.com', 'realauction', 'flagler-fl', 'scrape', true),
('Osceola', 'FL', 'https://www.property-appraiser.org', 'realauction', 'osceola-fl', 'scrape', true),
('Lake', 'FL', 'https://www.lakecopropappr.com', 'realauction', 'lake-fl', 'scrape', true),
('Alachua', 'FL', 'https://www.acpafl.org', 'realauction', 'alachua-fl', 'scrape', true),

-- North Carolina (6 counties) — govease / bid4assets
('Wake', 'NC', 'https://www.wakegov.com/departments-government/tax-administration', 'govease', 'wake-nc', 'scrape', true),
('Johnston', 'NC', 'https://www.johnstonnc.com/tax', 'govease', 'johnston-nc', 'scrape', true),
('Cabarrus', 'NC', 'https://www.cabarruscounty.us/government/tax', 'govease', 'cabarrus-nc', 'scrape', true),
('Union', 'NC', 'https://www.unioncountync.gov/government/departments/tax', 'bid4assets', 'union-nc', 'scrape', true),
('Iredell', 'NC', 'https://www.iredellcountync.gov/departments/tax', 'bid4assets', 'iredell-nc', 'scrape', true),
('Chatham', 'NC', 'https://www.chathamnc.org/government/departments-programs/tax', 'govease', 'chatham-nc', 'scrape', true)

ON CONFLICT DO NOTHING;
