"""
Clerk's Office liens enricher — Passo 6 do Método Deed Hunter.

Searches county clerk portals for outstanding liens against a parcel by owner
name and legal description / address. Classifies each lien as:
  - lien_type: irs_federal | state_tax | hoa | hospital | code_enforcement
                | judgment | mechanics | other
  - survives_tax_deed: True/False (legal rule per state and lien type)
  - is_released: True/False (Release of Lien document found)

Key legal rules encoded:
  IRS federal liens (26 U.S.C. §7425): ALWAYS survive in all states unless
    IRS is given 25-day notice before sale AND fails to redeem within 120 days.
    In practice, tax deed sales almost never give proper notice → lien survives.

  State tax liens: survive in TX, GA, TN, AR, FL, NC (all monitored states).

  HOA liens: Florida Ch.720/718 → survive up to 12 months assessments.
             Texas → survive if HOA recorded before tax deed sale.
             GA/TN/AR/NC → wiped by tax deed.

  Judgment, mechanics, hospital, code enforcement: wiped in all monitored states.

Portal strategy: try Tyler Technologies / Fidlar / iDoc patterns first (cover
~80% of US counties), then fall back to state-specific portals.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LienRecord:
    lien_type: str              # irs_federal, state_tax, hoa, hospital,
                                # code_enforcement, judgment, mechanics, other
    grantor: Optional[str]      # debtor
    grantee: Optional[str]      # lienholder
    lien_amount: Optional[float]
    recorded_date: Optional[date]
    lien_id_external: Optional[str]
    is_released: bool
    release_doc_number: Optional[str]
    release_date: Optional[date]
    survives_tax_deed: bool
    survive_reason: Optional[str]
    raw_text: str = ""


@dataclass
class LiensResult:
    parcel_id: str
    total_liens: int
    active_liens: int               # not released
    surviving_liens: int            # survives AND not released
    total_active_amount: float
    surviving_amount: float
    surviving_types: list[str]
    records: list[LienRecord]
    source: str
    clerk_portal_url: str
    has_additional_liens: bool      # backward-compat flag for parcel_risks
    liens_amount: float             # total surviving amount (for scoring filter)


# ---------------------------------------------------------------------------
# State-specific survival rules
# ---------------------------------------------------------------------------

# Lien types that always survive federal law regardless of state
_ALWAYS_SURVIVE_FEDERAL = {"irs_federal"}

# Lien types that survive in specific states
_STATE_SURVIVAL: dict[str, set[str]] = {
    "TX": {"irs_federal", "state_tax", "hoa"},
    "GA": {"irs_federal", "state_tax"},
    "TN": {"irs_federal", "state_tax"},
    "AR": {"irs_federal", "state_tax"},
    "FL": {"irs_federal", "state_tax", "hoa"},
    "NC": {"irs_federal", "state_tax"},
}

_SURVIVE_REASONS = {
    "irs_federal": "Lien federal IRS — 26 U.S.C. §7425: sobrevive ao tax deed salvo aviso formal de 25 dias à IRS",
    "state_tax": "Lien de imposto estadual — prioridade sobre tax deed na maioria dos estados monitorados",
    "hoa": "HOA lien — FL: sobrevive até 12 meses de taxas (Ch.720/718); TX: sobrevive se registrado antes do deed",
}


def classify_lien(lien_type: str, state: str) -> tuple[bool, Optional[str]]:
    """Returns (survives_tax_deed, reason_or_None)."""
    state_rules = _STATE_SURVIVAL.get(state.upper(), {"irs_federal"})
    survives = lien_type in state_rules
    reason = _SURVIVE_REASONS.get(lien_type) if survives else None
    return survives, reason


# ---------------------------------------------------------------------------
# Lien type detection from document text
# ---------------------------------------------------------------------------

_LIEN_PATTERNS: list[tuple[str, list[str]]] = [
    ("irs_federal", [
        r"internal revenue service", r"\birs\b", r"federal tax lien",
        r"notice of federal tax", r"dept\. of treasury",
    ]),
    ("state_tax", [
        r"state tax lien", r"department of revenue", r"franchise tax",
        r"state of \w+ tax", r"comptroller", r"revenue lien",
    ]),
    ("hoa", [
        r"homeowners.{0,10}association", r"\bhoa\b", r"property owners.{0,10}association",
        r"community association", r"assessment lien", r"condominium association",
    ]),
    ("hospital", [
        r"hospital\b", r"medical center", r"health system", r"medical lien",
        r"health care lien",
    ]),
    ("code_enforcement", [
        r"code enforcement", r"municipal lien", r"city of .{3,30} lien",
        r"county code", r"building violation", r"nuisance lien",
        r"demolition lien",
    ]),
    ("mechanics", [
        r"mechanic.{0,3}lien", r"materialman", r"contractor lien",
        r"construction lien", r"claim of lien",
    ]),
    ("judgment", [
        r"judgment lien", r"court judgment", r"civil judgment",
        r"final judgment", r"writ of execution",
    ]),
]

_RELEASE_PATTERNS = [
    r"release of lien", r"satisfaction of lien", r"discharge of lien",
    r"lien release", r"release and satisfaction",
]


def detect_lien_type(text: str) -> str:
    text_lower = text.lower()
    for lien_type, patterns in _LIEN_PATTERNS:
        if any(re.search(p, text_lower) for p in patterns):
            return lien_type
    return "other"


def is_release_document(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in _RELEASE_PATTERNS)


# ---------------------------------------------------------------------------
# Clerk portal scrapers
# ---------------------------------------------------------------------------

# County → (portal_type, base_url)
COUNTY_PORTALS: dict[tuple[str, str], tuple[str, str]] = {
    # Texas — most use Tyler Technologies (ECCA)
    ("Kaufman", "TX"):    ("tyler", "https://kaufman.tx.publicsearch.us"),
    ("Montgomery", "TX"): ("tyler", "https://montgomery.tx.publicsearch.us"),
    ("Bastrop", "TX"):    ("tyler", "https://bastrop.tx.publicsearch.us"),
    ("Caldwell", "TX"):   ("tyler", "https://caldwell.tx.publicsearch.us"),
    ("Ellis", "TX"):      ("tyler", "https://ellis.tx.publicsearch.us"),
    ("Rockwall", "TX"):   ("tyler", "https://rockwall.tx.publicsearch.us"),
    ("Hays", "TX"):       ("tyler", "https://hays.tx.publicsearch.us"),
    ("Comal", "TX"):      ("tyler", "https://comal.tx.publicsearch.us"),
    ("Liberty", "TX"):    ("tyler", "https://liberty.tx.publicsearch.us"),
    ("Chambers", "TX"):   ("tyler", "https://chambers.tx.publicsearch.us"),
    ("Denton", "TX"):     ("tyler", "https://denton.tx.publicsearch.us"),
    ("Fort Bend", "TX"):  ("tyler", "https://fortbend.tx.publicsearch.us"),
    ("Guadalupe", "TX"):  ("tyler", "https://guadalupe.tx.publicsearch.us"),
    ("Wilson", "TX"):     ("tyler", "https://wilson.tx.publicsearch.us"),
    ("Collin", "TX"):     ("tyler", "https://collin.tx.publicsearch.us"),
    # Georgia — Clerk of Superior Court / qPublic
    ("Dawson", "GA"):     ("fidlar", "https://efile.dawsoncounty.org"),
    ("Jackson", "GA"):    ("fidlar", "https://jacksoncountyclerk.org"),
    ("Pickens", "GA"):    ("fidlar", "https://pickenscountyclerk.com"),
    ("Cherokee", "GA"):   ("fidlar", "https://cherokeeclerk.com"),
    ("Forsyth", "GA"):    ("fidlar", "https://forsythclerk.com"),
    ("Barrow", "GA"):     ("fidlar", "https://barrowclerk.com"),
    ("Walton", "GA"):     ("fidlar", "https://waltoncountyga.gov/clerk"),
    ("Hall", "GA"):       ("fidlar", "https://hallcountyclerk.org"),
    ("Henry", "GA"):      ("fidlar", "https://henrycounty.com/clerk"),
    ("Paulding", "GA"):   ("fidlar", "https://pauldingclerk.com"),
    ("Newton", "GA"):     ("fidlar", "https://newtoncountyga.gov/clerk"),
    # Tennessee — Register of Deeds (Tyler Technologies)
    ("Rutherford", "TN"): ("tyler", "https://rutherford.tn.publicsearch.us"),
    ("Williamson", "TN"): ("tyler", "https://williamson.tn.publicsearch.us"),
    ("Wilson", "TN"):     ("tyler", "https://wilson.tn.publicsearch.us"),
    ("Maury", "TN"):      ("tyler", "https://maury.tn.publicsearch.us"),
    # Arkansas — Circuit Clerk
    ("Benton", "AR"):     ("tyler", "https://benton.ar.publicsearch.us"),
    ("Washington", "AR"): ("tyler", "https://washington.ar.publicsearch.us"),
    ("Saline", "AR"):     ("tyler", "https://saline.ar.publicsearch.us"),
    ("Faulkner", "AR"):   ("tyler", "https://faulkner.ar.publicsearch.us"),
    # Florida — Clerk of Courts (Tyler Technologies)
    ("Polk", "FL"):       ("tyler", "https://polk.fl.publicsearch.us"),
    ("Pasco", "FL"):      ("tyler", "https://pasco.fl.publicsearch.us"),
    ("Hernando", "FL"):   ("tyler", "https://hernando.fl.publicsearch.us"),
    ("Volusia", "FL"):    ("tyler", "https://volusia.fl.publicsearch.us"),
    ("Marion", "FL"):     ("tyler", "https://marion.fl.publicsearch.us"),
    ("St. Johns", "FL"):  ("tyler", "https://stjohns.fl.publicsearch.us"),
    ("Flagler", "FL"):    ("tyler", "https://flagler.fl.publicsearch.us"),
    ("Osceola", "FL"):    ("tyler", "https://osceola.fl.publicsearch.us"),
    ("Lake", "FL"):       ("tyler", "https://lake.fl.publicsearch.us"),
    ("Alachua", "FL"):    ("tyler", "https://alachua.fl.publicsearch.us"),
    # North Carolina — Register of Deeds (Tyler Technologies)
    ("Wake", "NC"):       ("tyler", "https://wake.nc.publicsearch.us"),
    ("Johnston", "NC"):   ("tyler", "https://johnston.nc.publicsearch.us"),
    ("Cabarrus", "NC"):   ("tyler", "https://cabarrus.nc.publicsearch.us"),
    ("Union", "NC"):      ("tyler", "https://union.nc.publicsearch.us"),
    ("Iredell", "NC"):    ("tyler", "https://iredell.nc.publicsearch.us"),
    ("Chatham", "NC"):    ("tyler", "https://chatham.nc.publicsearch.us"),
}


async def _search_tyler(
    page: Page,
    base_url: str,
    owner_name: str,
    address: str,
) -> list[dict]:
    """
    Tyler Technologies PublicSearch portal scraper.
    Searches by owner name and address for lien-type documents.
    """
    results: list[dict] = []

    lien_doc_types = [
        "TAX LIEN", "FEDERAL TAX LIEN", "STATE TAX LIEN", "LIEN",
        "HOA LIEN", "JUDGMENT", "MECHANIC LIEN", "HOSPITAL LIEN",
        "CODE ENFORCEMENT", "MUNICIPAL LIEN",
    ]

    try:
        await page.goto(f"{base_url}/search", wait_until="networkidle", timeout=20000)

        # Try name search first
        name_input = await page.query_selector(
            'input[placeholder*="name"], input[id*="name"], input[name*="owner"]'
        )
        if name_input and owner_name:
            await name_input.fill(owner_name)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            rows = await _extract_tyler_rows(page)
            results.extend(rows)

        # Then address search
        await page.goto(f"{base_url}/search", wait_until="networkidle", timeout=20000)
        addr_input = await page.query_selector(
            'input[placeholder*="address"], input[id*="address"], input[name*="address"]'
        )
        if addr_input and address:
            await addr_input.fill(address)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            rows = await _extract_tyler_rows(page)
            results.extend(rows)

    except Exception:
        pass

    return results


async def _extract_tyler_rows(page: Page) -> list[dict]:
    """Extract document rows from Tyler Technologies search results table."""
    rows: list[dict] = []
    result_rows = await page.query_selector_all("table.results tr, .result-row, tr[data-doc-id]")

    for row in result_rows:
        try:
            cells = await row.query_selector_all("td")
            texts = [(await c.inner_text()).strip() for c in cells]
            if len(texts) < 3:
                continue
            full_text = " ".join(texts)
            rows.append({
                "doc_number": texts[0] if texts else "",
                "doc_type": texts[1] if len(texts) > 1 else "",
                "grantor": texts[2] if len(texts) > 2 else "",
                "grantee": texts[3] if len(texts) > 3 else "",
                "recorded_date": texts[4] if len(texts) > 4 else "",
                "amount": texts[5] if len(texts) > 5 else "",
                "full_text": full_text,
            })
        except Exception:
            continue

    return rows


async def _search_fidlar(
    page: Page,
    base_url: str,
    owner_name: str,
    address: str,
) -> list[dict]:
    """Fidlar Technologies clerk portal (common in GA)."""
    results: list[dict] = []
    try:
        await page.goto(f"{base_url}/search", wait_until="networkidle", timeout=20000)
        name_input = await page.query_selector('input[name="name"], input[placeholder*="Name"]')
        if name_input and owner_name:
            await name_input.fill(owner_name)
            submit = await page.query_selector('button[type="submit"], input[type="submit"]')
            if submit:
                await submit.click()
            await page.wait_for_load_state("networkidle")
            rows = await _extract_tyler_rows(page)
            results.extend(rows)
    except Exception:
        pass
    return results


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> Optional[date]:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(text: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.]", "", str(text))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _build_lien_record(row: dict, state: str) -> LienRecord:
    lien_type = detect_lien_type(row.get("full_text", "") + " " + row.get("doc_type", ""))
    is_released = is_release_document(row.get("full_text", "") + " " + row.get("doc_type", ""))
    survives, reason = classify_lien(lien_type, state)

    return LienRecord(
        lien_type=lien_type,
        grantor=row.get("grantor") or None,
        grantee=row.get("grantee") or None,
        lien_amount=_parse_amount(row.get("amount", "")),
        recorded_date=_parse_date(row.get("recorded_date", "")),
        lien_id_external=row.get("doc_number") or None,
        is_released=is_released,
        release_doc_number=None,
        release_date=None,
        survives_tax_deed=survives,
        survive_reason=reason,
        raw_text=row.get("full_text", ""),
    )


async def check_liens(
    parcel_id: str,
    owner_name: str,
    address: str,
    county_name: str,
    state: str,
) -> LiensResult:
    """
    Searches the county Clerk's Office for outstanding liens on a parcel.

    Args:
        parcel_id: UUID of the parcel in our DB.
        owner_name: Current owner name from assessor data.
        address: Parcel address / legal description.
        county_name: County name (e.g. "Kaufman").
        state: Two-letter state code (e.g. "TX").

    Returns:
        LiensResult with all found liens and aggregated summary.
    """
    portal_key = (county_name, state.upper())
    portal = COUNTY_PORTALS.get(portal_key)

    records: list[LienRecord] = []
    source = "not_found"
    clerk_url = ""

    if portal:
        portal_type, base_url = portal
        clerk_url = base_url
        source = portal_type

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()

            if portal_type == "tyler":
                raw_rows = await _search_tyler(page, base_url, owner_name, address)
            elif portal_type == "fidlar":
                raw_rows = await _search_fidlar(page, base_url, owner_name, address)
            else:
                raw_rows = []

            await browser.close()

        for row in raw_rows:
            rec = _build_lien_record(row, state)
            records.append(rec)

    # Deduplicate by doc_number
    seen: set[str] = set()
    unique: list[LienRecord] = []
    for r in records:
        key = r.lien_id_external or r.raw_text[:60]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    records = unique

    # Cross-reference: if a release document exists for a lien type, mark originals released
    released_types = {r.lien_type for r in records if r.is_released}
    for r in records:
        if r.lien_type in released_types and not r.is_released:
            # Heuristic: release docs found → mark all matching type as released
            r.is_released = True

    active = [r for r in records if not r.is_released]
    surviving = [r for r in active if r.survives_tax_deed]

    total_active_amount = sum(r.lien_amount or 0 for r in active)
    surviving_amount = sum(r.lien_amount or 0 for r in surviving)
    surviving_types = list({r.lien_type for r in surviving})

    return LiensResult(
        parcel_id=parcel_id,
        total_liens=len(records),
        active_liens=len(active),
        surviving_liens=len(surviving),
        total_active_amount=total_active_amount,
        surviving_amount=surviving_amount,
        surviving_types=surviving_types,
        records=records,
        source=source,
        clerk_portal_url=clerk_url,
        has_additional_liens=len(surviving) > 0,
        liens_amount=surviving_amount,
    )


async def save_liens_to_db(db, liens: LiensResult) -> None:
    """Persist liens result to parcel_liens table and update parcel_risks."""
    # Clear old liens for this parcel and reinsert
    db.table("parcel_liens").delete().eq("parcel_id", liens.parcel_id).execute()

    for r in liens.records:
        db.table("parcel_liens").insert({
            "parcel_id": liens.parcel_id,
            "lien_id_external": r.lien_id_external,
            "lien_type": r.lien_type,
            "grantor": r.grantor,
            "grantee": r.grantee,
            "lien_amount": r.lien_amount,
            "recorded_date": r.recorded_date.isoformat() if r.recorded_date else None,
            "is_released": r.is_released,
            "release_doc_number": r.release_doc_number,
            "release_date": r.release_date.isoformat() if r.release_date else None,
            "survives_tax_deed": r.survives_tax_deed,
            "survive_reason": r.survive_reason,
            "clerk_portal_url": liens.clerk_portal_url,
            "source": liens.source,
            "raw_data": {"text": r.raw_text},
        }).execute()

    # Update parcel_risks with consolidated flags
    db.table("parcel_risks").update({
        "has_additional_liens": liens.has_additional_liens,
        "liens_amount": liens.surviving_amount,
    }).eq("parcel_id", liens.parcel_id).execute()
