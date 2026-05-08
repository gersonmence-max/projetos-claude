# EV Charger Site Analyzer — Design Document
**Date:** 2026-03-05
**Status:** Approved
**Use case:** Demo for clients/investors

---

## 1. Objective

Build a web tool that identifies the best locations in Massachusetts cities to install EV chargers (DCFC and Level 2), scoring each candidate site across 4 dimensions and presenting results in a professional demo-ready interface.

**Priority constraints:**
- Must never crash during a live demo (resilient fallbacks on every API)
- Results must appear genuinely intelligent and justified (not random)
- Export to PDF (for client) and CSV (for internal analysis)

---

## 2. Architecture

### Stack
- **Backend:** Flask (Python), port 5000
- **Frontend:** HTML/CSS/JavaScript, Leaflet.js for maps
- **Storage:** None — all data from external APIs or bundled static files

### File Structure
```
app.py                        ← Flask routes
api_clients.py                ← All API calls + fallback logic
scoring_engine.py             ← 4-component scoring engine
static/
  index.html                  ← Main page (city selector + map + ranking)
  detail.html                 ← Location detail page (scores + tools)
  app.js                      ← Frontend logic
  style.css                   ← Dark mode professional theme
data/
  nrel_ma_static.json         ← Bundled MA EV charger dataset (~800 stations)
  ma_city_demographics.json   ← Median income + population for all 351 MA cities
docs/plans/                   ← Design and implementation docs
```

### Request Flow
```
User selects "Cambridge" → POST /api/analyze
  → geocode_cidade()              → lat/lng
  → buscar_google_places()        → up to 150 candidate locations (6 types × 25)
  → For each candidate:
      obter_chargers_proximos()   → competition data
      obter_trafego_tomtom()      → congestion ratio
      obter_demographics_census() → income, population
  → eligibility_gate()            → filter rating < 2.0 with 100+ reviews
  → LocationScorer.score()        → DCFC + L2 scores for each
  → Return top 20 sorted by score
```

---

## 3. API Layer + Fallback Strategy

| API | Purpose | Fallback |
|-----|---------|----------|
| LocationIQ | Geocoding (primary) | → OpenCage → Nominatim |
| OpenCage | Geocoding (secondary) | → Nominatim |
| Nominatim | Geocoding (always works) | None needed |
| Google Places | Find candidate locations | None (reliable) |
| NREL | Existing chargers nearby | `data/nrel_ma_static.json` |
| TomTom | Traffic congestion | Review count proxy from Google Places |
| Census | Median income, population | `data/ma_city_demographics.json` |

**Rules:**
- All external API calls have a 4-second timeout (demo cannot freeze)
- Every function always returns a valid value — never `None` into the scoring engine
- If all fallbacks fail, use a neutral value (e.g., `congestion_ratio = 0.5`)

---

## 4. Scoring Engine

```
FINAL SCORE = Demand×0.35 + Competition×0.30 + SiteFit×0.20 + EVAffinity×0.15
```
Calculated separately for DCFC and Level 2. Scale: 0–10.

### Demand Score (35%)
- Input: `congestion_ratio` (0–1) from TomTom or review-count proxy
- Formula: sigmoid centered at 0.4
- DCFC variant: steeper curve (needs high traffic)
- L2 variant: shallower curve (tolerates moderate traffic)

### Competition Score (30%)
- Input: list of nearby chargers (lat/lng, type, distance)
- Formula: `score = 10 × exp(-Σ exp(-distance_km / 0.5))`
- 0 chargers within 1km → score 10; 3 chargers within 200m → score ~1.5

### Site Fit Score (20%)
- Input: Google Places `place_type`
- Lookup table (DCFC / L2):

| Type | DCFC | L2 |
|------|------|----|
| gas_station | 8.5 | 3.5 |
| shopping_mall | 7.0 | 9.0 |
| hotel | 5.0 | 9.5 |
| supermarket | 6.5 | 7.5 |
| restaurant | 4.0 | 6.0 |
| parking | 6.0 | 8.0 |

### EV Affinity Score (15%)
- Input: city median income + location name
- `income_score = min(median_income / 80000, 1.0) × 7`
- Brand bonus: +2.0 for Whole Foods/Tesla/Apple/Trader Joe's; +1.5 for Wegmans/REI/Target
- `final = min(income_score + brand_bonus, 10)`

### Eligibility Gate
- Discard: rating < 2.0 with 100+ reviews
- Everything else passes (maximize candidate pool)

---

## 5. Output Format (per location)

```json
{
  "name": "Arsenal Yards",
  "address": "485 Arsenal St, Watertown, MA",
  "rating": 4.3,
  "reviews": 1200,
  "lat": 42.3654,
  "lng": -71.1748,
  "dcfc_score": 8.2,
  "l2_score": 9.1,
  "confidence": 0.87,
  "breakdown": {
    "demand": 7.8,
    "competition": 9.2,
    "site_fit": 8.0,
    "ev_affinity": 8.5
  },
  "strengths": ["Alta renda local", "Sem concorrência em 1km"],
  "risks": ["Tráfego moderado nos fins de semana"]
}
```

---

## 6. Interface

### Main Page
- Header with city dropdown (341 MA cities) and "Analisar" button
- Split layout: Leaflet.js map (left) + ranked list (right)
- Map pins color-coded: green (>7.0), yellow (5.0–7.0), red (<5.0)
- Click pin or location name → navigate to detail page
- Export buttons appear after analysis completes

### Detail Page (second screen)
- Back button → return to ranking
- Location name, address, rating, review count
- DCFC and L2 score bars
- 4-component breakdown bars
- Strengths and risks list
- **Analysis Tools section:**
  - "Abrir no Google Maps" → `https://www.google.com/maps/search/EV+charging/@{lat},{lng},15z` (new tab)
  - "Google Street View" → `https://www.google.com/maps/@{lat},{lng},3a,75y,0h,90t/data=!3m1!1e1` (new tab)

### Visual Design
- Dark mode dashboard aesthetic
- Electric green/blue accent colors
- Professional font, clean card layout

---

## 7. Export

### PDF (WeasyPrint)
- Page 1: Cover (city, date)
- Page 2: Executive summary (total analyzed, viable count, top recommendation)
- Pages 3+: Top 20 locations (name, address, scores, breakdown, strengths/risks)
- Footer: brief methodology note

### CSV
All 20 locations, one row each:
`name, address, rating, reviews, lat, lng, dcfc_score, l2_score, confidence, demand, competition, site_fit, ev_affinity, chargers_nearby, median_income, congestion_ratio`

---

## 8. Environment Variables (.env)

```
GOOGLE_PLACES_API_KEY=
LOCATIONIQ_API_KEY=
OPENCAGE_API_KEY=
TOMTOM_API_KEY=
NREL_API_KEY=
CENSUS_API_KEY=
```

No comments, no extra lines — exact format required.
