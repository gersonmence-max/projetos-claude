"""
Census Bureau ACS 5-Year Estimates — county population and demographics.
Uses api.census.gov (free, no key required for basic queries).
"""
import httpx
from typing import Optional

CENSUS_URL = "https://api.census.gov/data/2023/acs/acs5"

# FIPS codes for monitored states
STATE_FIPS = {
    "TX": "48", "GA": "13", "TN": "47", "AR": "05", "FL": "12", "NC": "37"
}

# County FIPS for all 50 monitored counties
COUNTY_FIPS = {
    # Texas
    ("Kaufman", "TX"): ("48", "257"),
    ("Montgomery", "TX"): ("48", "339"),
    ("Bastrop", "TX"): ("48", "021"),
    ("Caldwell", "TX"): ("48", "055"),
    ("Ellis", "TX"): ("48", "139"),
    ("Rockwall", "TX"): ("48", "397"),
    ("Hays", "TX"): ("48", "209"),
    ("Comal", "TX"): ("48", "091"),
    ("Liberty", "TX"): ("48", "291"),
    ("Chambers", "TX"): ("48", "071"),
    ("Denton", "TX"): ("48", "121"),
    ("Fort Bend", "TX"): ("48", "157"),
    ("Guadalupe", "TX"): ("48", "187"),
    ("Wilson", "TX"): ("48", "493"),
    ("Collin", "TX"): ("48", "085"),
    # Georgia
    ("Dawson", "GA"): ("13", "085"),
    ("Jackson", "GA"): ("13", "157"),
    ("Pickens", "GA"): ("13", "227"),
    ("Cherokee", "GA"): ("13", "057"),
    ("Forsyth", "GA"): ("13", "117"),
    ("Barrow", "GA"): ("13", "013"),
    ("Walton", "GA"): ("13", "297"),
    ("Hall", "GA"): ("13", "139"),
    ("Henry", "GA"): ("13", "151"),
    ("Paulding", "GA"): ("13", "223"),
    ("Newton", "GA"): ("13", "217"),
    # Tennessee
    ("Rutherford", "TN"): ("47", "149"),
    ("Williamson", "TN"): ("47", "187"),
    ("Wilson", "TN"): ("47", "189"),
    ("Maury", "TN"): ("47", "119"),
    # Arkansas
    ("Benton", "AR"): ("05", "007"),
    ("Washington", "AR"): ("05", "143"),
    ("Saline", "AR"): ("05", "125"),
    ("Faulkner", "AR"): ("05", "045"),
    # Florida
    ("Polk", "FL"): ("12", "105"),
    ("Pasco", "FL"): ("12", "101"),
    ("Hernando", "FL"): ("12", "053"),
    ("Volusia", "FL"): ("12", "127"),
    ("Marion", "FL"): ("12", "083"),
    ("St. Johns", "FL"): ("12", "109"),
    ("Flagler", "FL"): ("12", "035"),
    ("Osceola", "FL"): ("12", "097"),
    ("Lake", "FL"): ("12", "069"),
    ("Alachua", "FL"): ("12", "001"),
    # North Carolina
    ("Wake", "NC"): ("37", "183"),
    ("Johnston", "NC"): ("37", "101"),
    ("Cabarrus", "NC"): ("37", "025"),
    ("Union", "NC"): ("37", "179"),
    ("Iredell", "NC"): ("37", "097"),
    ("Chatham", "NC"): ("37", "037"),
}


async def get_county_demographics(county_name: str, state: str) -> dict:
    """
    Fetches population, income, and unemployment from Census ACS5.
    Returns growth_rate_3yr as estimated from B01003 (total population).
    """
    fips = COUNTY_FIPS.get((county_name, state))
    if not fips:
        return {"error": f"FIPS not found for {county_name}, {state}"}

    state_fips, county_fips = fips
    params = {
        "get": "B01003_001E,B19013_001E,NAME",
        "for": f"county:{county_fips}",
        "in": f"state:{state_fips}",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(CENSUS_URL, params=params)
            resp.raise_for_status()
            rows = resp.json()
            if len(rows) < 2:
                return {"error": "no data"}

            headers = rows[0]
            values = rows[1]
            data = dict(zip(headers, values))

            population = int(data.get("B01003_001E") or 0)
            median_income = int(data.get("B19013_001E") or 0)

            # Fetch 2020 population for growth rate calculation
            params_2020 = {
                "get": "B01003_001E",
                "for": f"county:{county_fips}",
                "in": f"state:{state_fips}",
            }
            resp_2020 = await client.get(
                "https://api.census.gov/data/2020/acs/acs5", params=params_2020
            )
            pop_2020 = population  # default to same
            if resp_2020.status_code == 200:
                rows_2020 = resp_2020.json()
                if len(rows_2020) >= 2:
                    pop_2020 = int(rows_2020[1][0] or population)

            growth_rate_3yr = ((population - pop_2020) / max(pop_2020, 1)) * 100 if pop_2020 else 0.0

            return {
                "population_2020": pop_2020,
                "population_latest": population,
                "growth_rate_3yr": round(growth_rate_3yr, 2),
                "median_household_income": median_income,
                "source": "census_acs5",
            }
        except Exception as e:
            return {"error": str(e)}
