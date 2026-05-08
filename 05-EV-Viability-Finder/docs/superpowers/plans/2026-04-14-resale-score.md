# Resale Score System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing multi-factor scorer with a 3-component score (Discount + Liquidity + FEMA) and FORTE/MODERADO/FRACO/EVITAR classifier focused on real resale potential.

**Architecture:** Pipeline enrichment fixes the discount calculation (per-acre, no market multipliers). Scorer reads pre-computed `discount_pct`. Classifier replaces flip/buy_hold/avoid. Frontend sorts FORTE→MODERADO, hides empty fields, shows score breakdown in detail.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), React + TypeScript + Tailwind, pytest

---

## Files Modified / Created

| File | Change |
|---|---|
| `backend/enrichers/zillow_market.py` | Remove ×0.15/×0.20 multipliers; return raw median home value |
| `backend/routes/pipeline.py` | Fix discount_pct to use price/acre vs raw median |
| `backend/filters.py` | Hard-eliminate A/AE/AO/AH/VE/V + population<2500; acreage threshold 0.10 |
| `backend/scorer.py` | 3-component score; add `calculate_score_breakdown()` |
| `backend/classifier.py` | Rewrite → FORTE/MODERADO/FRACO/EVITAR |
| `backend/models.py` | Add `classification` column |
| `backend/routes/properties.py` | Sort FORTE→MODERADO; add `classification` filter; expose breakdown |
| `backend/tests/test_scorer.py` | Rewrite for new formula |
| `backend/tests/test_classifier.py` | Rewrite for FORTE/MODERADO/FRACO/EVITAR |
| `backend/tests/test_junk_filter.py` | Update threshold 0.10; add AO/AH cases |
| `backend/tests/test_filters.py` | Add population and FEMA hard-elimination tests |
| `frontend/src/types.ts` | Add `classification`, `score_breakdown`; update `PropertyFilters` |
| `frontend/src/api/properties.ts` | Add `classification` + `county` params |
| `frontend/src/components/FilterPanel.tsx` | Add Classification + County filters |
| `frontend/src/components/PropertyTable.tsx` | New column set; remove Tipo/Risco/Veredicto |
| `frontend/src/pages/Dashboard.tsx` | Stats: FORTE/MODERADO counts |
| `frontend/src/pages/PropertyDetail.tsx` | Score breakdown; hide empty fields; AI hidden by default |
| `CLAUDE.md` | Update system description |

---

## Task 1: Remove market multipliers from zillow_market.py

**Files:**
- Modify: `backend/enrichers/zillow_market.py`

- [ ] **Step 1: Remove `_LAND_FRACTION` constants and apply them in builders**

In `_build_from_redfin`, line ~118: change `result[key] = median_price * _LAND_FRACTION` → `result[key] = median_price`

In `_fetch_state_medians_census`, line ~156: change `result[county_name] = median_home * _LAND_FRACTION_CENSUS` → `result[county_name] = median_home`

Remove the two constant definitions at the top of the file:
```python
# DELETE these two lines:
_LAND_FRACTION = 0.15
_LAND_FRACTION_CENSUS = 0.20
```

- [ ] **Step 2: Verify `get_market_median` still works (no change needed to its body)**

Read the `get_market_median` function — confirm it just returns from `_market_cache` with no multiplier of its own. If there is one, remove it.

- [ ] **Step 3: Commit**

```bash
git add backend/enrichers/zillow_market.py
git commit -m "fix: remove x0.15/x0.20 land fraction multipliers from market cache"
```

---

## Task 2: Fix discount_pct computation in pipeline.py

**Files:**
- Modify: `backend/routes/pipeline.py` (lines ~158–171)

- [ ] **Step 1: Replace the discount_pct block**

Find this block (around line 157):
```python
market_median = get_market_median(
    listing.get("county", ""), listing.get("state", "")
)
if market_median and price and market_median > 0:
    listing["discount_pct"] = (1 - price / market_median) * 100
else:
    assessed = listing.get("assessed_value")
    if assessed and price and assessed > 0:
        listing["discount_pct"] = (1 - price / assessed) * 100
    else:
        avg_ppa = listing.get("avg_price_per_acre")
        ppa = listing.get("price_per_acre")
        if avg_ppa and ppa and avg_ppa > 0:
            listing["discount_pct"] = (1 - ppa / avg_ppa) * 100
```

Replace with:
```python
market_median = get_market_median(
    listing.get("county", ""), listing.get("state", "")
)
if market_median and price and market_median > 0:
    acres = listing.get("acres")
    if acres and acres > 0:
        price_per_acre = price / acres
        listing["discount_pct"] = (1 - price_per_acre / market_median) * 100
    else:
        listing["discount_pct"] = (1 - price / market_median) * 100
```

The fallback chain (assessed_value, avg_ppa) is removed — those were estimates without real data.

- [ ] **Step 2: Commit**

```bash
git add backend/routes/pipeline.py
git commit -m "fix: compute discount_pct as price/acre vs raw median home value"
```

---

## Task 3: Update filters.py

**Files:**
- Modify: `backend/filters.py`

- [ ] **Step 1: Update `is_junk_property` acreage threshold from 0.02 to 0.10**

Find line: `if acres is not None and 0 < acres < 0.02:`
Change to: `if acres is not None and 0 < acres < 0.10:`

- [ ] **Step 2: Add hard FEMA + population elimination to `apply_filters`**

Replace the entire `apply_filters` function body with:
```python
def apply_filters(
    property_data: Dict[str, Any],
    config: FilterConfig,
    regrid_available: bool,
) -> bool:
    """Retorna True se a propriedade passa em todos os filtros."""

    # ── Hard eliminations (always applied) ───────────────────────────
    fema_zone = (property_data.get("fema_zone") or "").upper()
    if fema_zone in ("A", "AE", "AO", "AH", "VE", "V"):
        return False

    population = property_data.get("population")
    if population is not None and 0 < population < 2_500:
        return False

    # ── Configurable filters ──────────────────────────────────────────
    price = property_data.get("price")
    if price is not None and price > config.max_price:
        return False

    acres = property_data.get("acres")
    if acres is not None and acres < config.min_acres:
        return False

    if regrid_available:
        discount_pct = property_data.get("discount_pct")
        if discount_pct is not None and discount_pct < config.min_discount_pct:
            return False

        price_per_acre = property_data.get("price_per_acre")
        if price_per_acre is not None and price_per_acre > config.max_price_per_acre:
            return False

    return True
```

Also remove `only_fema_x` from `FilterConfig` since FEMA is now a hard elimination:
```python
@dataclass
class FilterConfig:
    max_price: float = 500_000
    min_acres: float = 0.0
    min_discount_pct: float = 10.0
    max_price_per_acre: float = 10_000
```

- [ ] **Step 3: Commit**

```bash
git add backend/filters.py
git commit -m "fix: hard-eliminate FEMA A/AE/AO/AH/VE/V and pop<2500; acreage threshold 0.10"
```

---

## Task 4: Rewrite scorer.py

**Files:**
- Modify: `backend/scorer.py`

- [ ] **Step 1: Replace `calculate_score` and add `calculate_score_breakdown`**

Replace the entire `scorer.py` with:
```python
# backend/scorer.py
import json
import math
from typing import Any, Dict, Optional

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY

_client: Optional[AsyncAnthropic] = None


def _get_client() -> Optional[AsyncAnthropic]:
    global _client
    if ANTHROPIC_API_KEY and _client is None:
        _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def calculate_score_breakdown(property_data: Dict[str, Any]) -> Dict[str, float]:
    """Retorna pontuação de cada componente: {a_pts, b_pts, c_pts}."""
    discount_pct = property_data.get("discount_pct") or 0.0
    fema_zone    = (property_data.get("fema_zone") or "").upper()
    population   = property_data.get("population") or 0
    income       = property_data.get("median_hh_income") or 0.0

    # A. Desconto (50 pts)
    a_pts = min(discount_pct / 80.0 * 50.0, 50.0) if discount_pct > 0 else 0.0

    # B. Liquidez (35 pts)
    if population >= 50_000:
        pop_pts = 20.0
    elif population >= 10_000:
        pop_pts = (population - 10_000) / 40_000 * 20.0
    elif population >= 2_500:
        pop_pts = (population - 2_500) / 7_500 * 8.0
    else:
        pop_pts = 0.0

    if income >= 55_000:
        inc_pts = 15.0
    elif income >= 35_000:
        inc_pts = (income - 35_000) / 20_000 * 15.0
    elif income >= 25_000:
        inc_pts = (income - 25_000) / 10_000 * 5.0
    else:
        inc_pts = 0.0

    b_pts = pop_pts + inc_pts

    # C. FEMA (15 pts)
    if not fema_zone:
        c_pts = 5.0
    elif fema_zone == "X":
        c_pts = 15.0
    elif fema_zone in ("X500", "B"):
        c_pts = 10.0
    elif fema_zone == "C":
        c_pts = 7.0
    else:
        c_pts = 0.0

    return {"a_pts": round(a_pts, 1), "b_pts": round(b_pts, 1), "c_pts": round(c_pts, 1)}


def calculate_score(property_data: Dict[str, Any]) -> float:
    """Score 0-100: A(desconto 50) + B(liquidez 35) + C(FEMA 15). Sem penalidades."""
    bd = calculate_score_breakdown(property_data)
    total = bd["a_pts"] + bd["b_pts"] + bd["c_pts"]
    return round(min(max(total, 0.0), 100.0), 1)


async def generate_ai_analysis(property_data: Dict[str, Any]) -> Optional[Dict]:
    """Gera análise textual do Claude para terrenos com score >= 70.

    Desabilitada por padrão — chame explicitamente quando necessário.
    """
    client = _get_client()
    if not client:
        return None

    if (property_data.get("score") or 0) < 70:
        return None

    prompt = f"""Analise este terreno nos EUA e responda em JSON.

Dados:
- Endereço: {property_data.get("address", "N/A")}
- Estado: {property_data.get("state", "N/A")} | Condado: {property_data.get("county", "N/A")}
- Preço total: ${property_data.get("price", 0):,.0f}
- Tamanho: {property_data.get("acres", 0):.1f} acres
- Preço/acre: ${property_data.get("price_per_acre", 0):,.0f}
- Desconto vs. mercado: {property_data.get("discount_pct", 0):.1f}%
- Zona FEMA: {property_data.get("fema_zone", "N/A")}
- Score calculado: {property_data.get("score", 0)}/100

Responda SOMENTE com JSON válido, sem texto adicional:
{{
  "resumo": "2-3 frases explicando por que este terreno é interessante ou não",
  "pontos_positivos": ["ponto 1", "ponto 2", "ponto 3"],
  "pontos_atencao": ["ponto 1", "ponto 2"],
  "veredicto": "Oportunidade forte"
}}

O veredicto deve ser exatamente um de: "Oportunidade forte", "Merece análise", "Cautela"."""

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(message.content[0].text)
    except Exception as e:
        print(f"Erro ao gerar análise Claude: {e}")
        return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/scorer.py
git commit -m "feat: 3-component score (discount+liquidity+FEMA) with breakdown; no penalties"
```

---

## Task 5: Rewrite classifier.py

**Files:**
- Modify: `backend/classifier.py`

- [ ] **Step 1: Replace entire classifier**

```python
# backend/classifier.py
"""Classifica terrenos em FORTE / MODERADO / FRACO / EVITAR."""
from typing import Any, Dict


def classify_property(prop: Dict[str, Any]) -> Dict[str, str]:
    """Retorna {"classification": "FORTE"|"MODERADO"|"FRACO"|"EVITAR"}."""
    score        = prop.get("score") or 0.0
    discount_pct = prop.get("discount_pct") or 0.0
    fema_zone    = (prop.get("fema_zone") or "").upper()
    population   = prop.get("population") or 0

    fema_safe  = fema_zone in ("X", "X500", "B")
    big_market = population >= 15_000
    big_disc   = discount_pct >= 50.0

    # EVITAR — checagens de segurança
    if fema_zone in ("A", "AE") and score < 65:
        return {"classification": "EVITAR"}
    if 0 < population < 5_000 and score < 70:
        return {"classification": "EVITAR"}

    # FORTE — todos os 3 critérios
    if score >= 75 and fema_safe and big_market and big_disc:
        return {"classification": "FORTE"}

    # MODERADO — pelo menos 2 dos 3 critérios
    criteria = sum([fema_safe, big_market, big_disc])
    if score >= 55 and criteria >= 2:
        return {"classification": "MODERADO"}

    return {"classification": "FRACO"}


# Manter alias para compatibilidade com pipeline (será atualizado em Task 6)
def classify_investment(prop: Dict[str, Any]) -> Dict[str, str]:
    return classify_property(prop)
```

- [ ] **Step 2: Update pipeline.py import to use new function name**

In `pipeline.py` line 12, change:
```python
from classifier import classify_investment
```
to:
```python
from classifier import classify_property
```

And line ~198: change `classify_investment(listing)` → `classify_property(listing)`.

- [ ] **Step 3: Commit**

```bash
git add backend/classifier.py backend/routes/pipeline.py
git commit -m "feat: classifier rewrite — FORTE/MODERADO/FRACO/EVITAR"
```

---

## Task 6: Add `classification` column to models.py

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Add column to Property model**

After the `risk_flags` line, add:
```python
classification = Column(String, nullable=True)  # "FORTE", "MODERADO", "FRACO", "EVITAR"
```

- [ ] **Step 2: Migrate existing SQLite DB**

Run this once to add the column without losing data:
```bash
cd backend
python -c "
from database import engine
with engine.connect() as conn:
    try:
        conn.execute('ALTER TABLE properties ADD COLUMN classification TEXT')
        conn.commit()
        print('Column added')
    except Exception as e:
        print(f'Already exists or error: {e}')
"
```

If the DB doesn't exist yet (fresh install), skip — `create_all()` will handle it.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: add classification column to Property model"
```

---

## Task 7: Update routes/properties.py

**Files:**
- Modify: `backend/routes/properties.py`

- [ ] **Step 1: Replace the entire file**

```python
# backend/routes/properties.py
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case as sql_case
from sqlalchemy.orm import Session

from database import get_db
from models import Property
from scorer import calculate_score_breakdown

router = APIRouter(prefix="/properties", tags=["properties"])

_CLASSIFICATION_ORDER = sql_case(
    (Property.classification == "FORTE", 1),
    (Property.classification == "MODERADO", 2),
    (Property.classification == "FRACO", 3),
    (Property.classification == "EVITAR", 4),
    else_=5,
)


def _prop_to_dict(p: Property, include_breakdown: bool = False) -> Dict[str, Any]:
    ai_analysis = None
    if p.ai_analysis:
        try:
            ai_analysis = json.loads(p.ai_analysis)
        except Exception:
            pass

    result: Dict[str, Any] = {
        "id": p.id,
        "source": p.source,
        "state": p.state,
        "county": p.county,
        "address": p.address,
        "lat": p.lat,
        "lng": p.lng,
        "price": p.price,
        "acres": p.acres,
        "price_per_acre": p.price_per_acre,
        "discount_pct": p.discount_pct,
        "fema_zone": p.fema_zone,
        "score": p.score,
        "classification": p.classification,
        "ai_analysis": ai_analysis,
        "listing_url": p.listing_url,
        "parcel_id": p.parcel_id,
        "sale_date": p.sale_date,
        "scraped_at": p.scraped_at.isoformat() if p.scraped_at else None,
        "passed_filters": p.passed_filters,
        "population": p.population,
        "median_hh_income": p.median_hh_income,
    }

    if include_breakdown:
        result["score_breakdown"] = calculate_score_breakdown({
            "discount_pct": p.discount_pct,
            "fema_zone": p.fema_zone,
            "population": p.population,
            "median_hh_income": p.median_hh_income,
        })

    return result


@router.get("/")
def list_properties(
    state: Optional[str] = None,
    county: Optional[str] = None,
    classification: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=100),
    max_price: Optional[float] = Query(None),
    min_acres: Optional[float] = Query(None),
    max_price_per_acre: Optional[float] = Query(None),
    min_discount_pct: Optional[float] = Query(None),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Property).filter(Property.passed_filters == True)

    if state:
        q = q.filter(Property.state == state)
    if county:
        q = q.filter(Property.county.ilike(f"%{county}%"))
    if classification:
        q = q.filter(Property.classification == classification.upper())
    if min_score:
        q = q.filter(Property.score >= min_score)
    if max_price is not None:
        q = q.filter(Property.price <= max_price)
    if min_acres is not None:
        q = q.filter(Property.acres >= min_acres)
    if max_price_per_acre is not None:
        q = q.filter(Property.price_per_acre <= max_price_per_acre)
    if min_discount_pct is not None:
        q = q.filter(Property.discount_pct >= min_discount_pct)

    props = q.order_by(_CLASSIFICATION_ORDER, Property.score.desc()).limit(limit).all()
    return [_prop_to_dict(p) for p in props]


@router.get("/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Propriedade não encontrada")
    return _prop_to_dict(prop, include_breakdown=True)
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/properties.py
git commit -m "feat: sort by classification, add county/classification filters, include score breakdown"
```

---

## Task 8: Rewrite test_scorer.py

**Files:**
- Modify: `backend/tests/test_scorer.py`

- [ ] **Step 1: Replace entire file**

```python
# backend/tests/test_scorer.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scorer import calculate_score, calculate_score_breakdown


# ── Score geral ──────────────────────────────────────────────────────────────

def test_score_vazio_retorna_zero():
    assert calculate_score({}) == 0.0


def test_score_sempre_entre_0_e_100():
    prop = {"discount_pct": 999, "fema_zone": "X",
            "population": 999_999, "median_hh_income": 999_999}
    assert 0.0 <= calculate_score(prop) <= 100.0


def test_score_desconto_alto_pontua_bem():
    prop = {"discount_pct": 80}
    assert calculate_score(prop) >= 50.0


def test_score_desconto_zero_pontua_zero_no_componente_a():
    prop = {"discount_pct": 0, "fema_zone": "X",
            "population": 60_000, "median_hh_income": 60_000}
    score = calculate_score(prop)
    bd = calculate_score_breakdown(prop)
    assert bd["a_pts"] == 0.0
    assert score == bd["b_pts"] + bd["c_pts"]


def test_maior_desconto_maior_score():
    alto = {"discount_pct": 90}
    baixo = {"discount_pct": 30}
    assert calculate_score(alto) > calculate_score(baixo)


# ── Componente A ─────────────────────────────────────────────────────────────

def test_componente_a_maximo_80pct_desconto():
    bd = calculate_score_breakdown({"discount_pct": 80})
    assert bd["a_pts"] == 50.0


def test_componente_a_desconto_negativo_zero_pts():
    bd = calculate_score_breakdown({"discount_pct": -10})
    assert bd["a_pts"] == 0.0


# ── Componente B — Liquidez ──────────────────────────────────────────────────

def test_populacao_50k_maximo():
    bd = calculate_score_breakdown({"discount_pct": 0, "population": 50_000})
    assert bd["b_pts"] == 20.0


def test_populacao_abaixo_2500_zero_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "population": 2_000})
    assert bd["b_pts"] == 0.0


def test_renda_55k_maximo():
    bd = calculate_score_breakdown({"discount_pct": 0, "median_hh_income": 55_000})
    assert bd["b_pts"] == 15.0


def test_renda_abaixo_25k_zero_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "median_hh_income": 20_000})
    assert bd["b_pts"] == 0.0


def test_liquidez_maxima():
    bd = calculate_score_breakdown({
        "discount_pct": 0, "population": 60_000, "median_hh_income": 60_000
    })
    assert bd["b_pts"] == 35.0


# ── Componente C — FEMA ──────────────────────────────────────────────────────

def test_fema_x_15_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": "X"})
    assert bd["c_pts"] == 15.0


def test_fema_x500_10_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": "X500"})
    assert bd["c_pts"] == 10.0


def test_fema_b_10_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": "B"})
    assert bd["c_pts"] == 10.0


def test_fema_c_7_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": "C"})
    assert bd["c_pts"] == 7.0


def test_sem_fema_5_pts_neutro():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": None})
    assert bd["c_pts"] == 5.0


def test_fema_ae_zero_pts():
    bd = calculate_score_breakdown({"discount_pct": 0, "fema_zone": "AE"})
    assert bd["c_pts"] == 0.0


# ── Score total exemplar ─────────────────────────────────────────────────────

def test_score_forte_esperado():
    # 80% discount (50pts) + pop=60k/inc=60k (35pts) + FEMA X (15pts) = 100
    prop = {"discount_pct": 80, "population": 60_000, "median_hh_income": 60_000, "fema_zone": "X"}
    assert calculate_score(prop) == 100.0
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_scorer.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_scorer.py
git commit -m "test: rewrite test_scorer for 3-component score"
```

---

## Task 9: Rewrite test_classifier.py

**Files:**
- Modify: `backend/tests/test_classifier.py`

- [ ] **Step 1: Replace entire file**

```python
# backend/tests/test_classifier.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from classifier import classify_property


def _c(**kw):
    return classify_property(kw)["classification"]


# ── FORTE ────────────────────────────────────────────────────────────────────

def test_forte_todos_criterios():
    r = _c(score=80, discount_pct=60, population=20_000, fema_zone="X")
    assert r == "FORTE"


def test_forte_exige_score_75():
    r = _c(score=74, discount_pct=60, population=20_000, fema_zone="X")
    assert r != "FORTE"


def test_forte_exige_fema_safe():
    r = _c(score=80, discount_pct=60, population=20_000, fema_zone="C")
    assert r != "FORTE"


def test_forte_exige_populacao_15k():
    r = _c(score=80, discount_pct=60, population=14_000, fema_zone="X")
    assert r != "FORTE"


def test_forte_exige_desconto_50():
    r = _c(score=80, discount_pct=49, population=20_000, fema_zone="X")
    assert r != "FORTE"


# ── MODERADO ─────────────────────────────────────────────────────────────────

def test_moderado_dois_de_tres_criterios():
    # fema_safe + big_market, mas discount < 50
    r = _c(score=60, discount_pct=30, population=20_000, fema_zone="X")
    assert r == "MODERADO"


def test_moderado_exige_score_55():
    r = _c(score=54, discount_pct=60, population=20_000, fema_zone="X")
    assert r != "MODERADO"


def test_moderado_fema_b_conta_como_safe():
    r = _c(score=60, discount_pct=30, population=20_000, fema_zone="B")
    assert r == "MODERADO"


# ── FRACO ────────────────────────────────────────────────────────────────────

def test_fraco_apenas_um_criterio():
    r = _c(score=56, discount_pct=60, population=5_000, fema_zone="C")
    assert r == "FRACO"


def test_fraco_score_baixo():
    r = _c(score=30, discount_pct=20, population=10_000, fema_zone="X")
    assert r == "FRACO"


def test_sem_dados_retorna_fraco():
    r = _c(score=0)
    assert r == "FRACO"


# ── EVITAR ───────────────────────────────────────────────────────────────────

def test_evitar_fema_ae_score_baixo():
    r = _c(score=60, discount_pct=70, population=30_000, fema_zone="AE")
    assert r == "EVITAR"


def test_evitar_fema_a_score_baixo():
    r = _c(score=50, discount_pct=80, population=50_000, fema_zone="A")
    assert r == "EVITAR"


def test_nao_evitar_fema_ae_score_alto():
    # AE com score >= 65 → não é EVITAR automático
    r = _c(score=65, discount_pct=80, population=50_000, fema_zone="AE")
    assert r != "EVITAR"


def test_evitar_populacao_pequena_score_baixo():
    r = _c(score=60, discount_pct=70, population=3_000, fema_zone="X")
    assert r == "EVITAR"


def test_nao_evitar_populacao_pequena_score_alto():
    r = _c(score=75, discount_pct=80, population=3_000, fema_zone="X")
    assert r != "EVITAR"
```

- [ ] **Step 2: Run tests**

```bash
cd backend && pytest tests/test_classifier.py -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_classifier.py
git commit -m "test: rewrite test_classifier for FORTE/MODERADO/FRACO/EVITAR"
```

---

## Task 10: Update test_junk_filter.py + test_filters.py

**Files:**
- Modify: `backend/tests/test_junk_filter.py`
- Modify: `backend/tests/test_filters.py`

- [ ] **Step 1: Update test_junk_filter.py for new 0.10 acreage threshold**

Update `test_acres_minimo_e_junk`:
```python
def test_acres_minimo_e_junk():
    # 0.09 < 0.10 → junk
    assert is_junk_property({"acres": 0.09, "address": "123 Main St"}) is True

def test_acres_limite_nao_e_junk():
    # 0.10 >= 0.10 → not junk
    assert is_junk_property({"acres": 0.10, "address": "123 Main St"}) is False
```

Also keep existing test `test_acres_zero_nao_filtrado` unchanged (0.0 = unknown, not junk).

Remove the old `test_fema_ae_nao_e_junk` if it exists (now AE is filtered in apply_filters, not junk filter):
- Verify if test file has `test_fema_ae_nao_e_junk` — if so, update its name/doc to clarify it's about the junk filter specifically, or keep as-is since AE is still not junk at this stage.

- [ ] **Step 2: Update test_filters.py — add hard elimination tests**

Add these test functions to `test_filters.py`:
```python
def test_fema_ao_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "AO"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_fema_ah_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "AH"}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_populacao_abaixo_2500_eliminado():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": 2_000}
    assert apply_filters(prop, config, regrid_available=False) is False


def test_populacao_2500_passa():
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": 2_500}
    assert apply_filters(prop, config, regrid_available=False) is True


def test_populacao_none_nao_eliminado():
    # sem dado de população → não elimina (dado ausente ≠ pequeno)
    config = FilterConfig()
    prop = {"price": 100_000, "acres": 5, "fema_zone": "X", "population": None}
    assert apply_filters(prop, config, regrid_available=False) is True
```

Update existing `test_zona_fema_exclui_risco_inundacao` to also verify AE is still blocked (now hard elimination, not only_fema_x):
```python
def test_zona_fema_exclui_risco_inundacao():
    config = FilterConfig()
    for zone in ("A", "AE", "AO", "AH", "VE", "V"):
        prop = {"price": 100_000, "acres": 5, "fema_zone": zone}
        assert apply_filters(prop, config, regrid_available=False) is False, f"{zone} should be rejected"
```

Remove or update `test_zona_fema_x_passa` to confirm X still passes (unchanged).

- [ ] **Step 3: Run all filter tests**

```bash
cd backend && pytest tests/test_filters.py tests/test_junk_filter.py -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_filters.py backend/tests/test_junk_filter.py
git commit -m "test: update filter tests for new FEMA/acreage/population thresholds"
```

---

## Task 11: Run full test suite

- [ ] **Step 1: Run all backend tests**

```bash
cd backend && pytest tests/ -v
```

Expected: all pass. Fix any failures before proceeding.

- [ ] **Step 2: Commit if there were fixes**

```bash
git add -p
git commit -m "fix: resolve test failures after score/filter/classifier rewrite"
```

---

## Task 12: Update frontend types.ts

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Replace the file**

```typescript
export interface AiAnalysis {
  resumo: string;
  pontos_positivos: string[];
  pontos_atencao: string[];
  veredicto: "Oportunidade forte" | "Merece análise" | "Cautela";
}

export interface ScoreBreakdown {
  a_pts: number;
  b_pts: number;
  c_pts: number;
}

export interface Property {
  id: number;
  source: string;
  state: string;
  county: string;
  address: string;
  lat: number | null;
  lng: number | null;
  price: number | null;
  acres: number | null;
  price_per_acre: number | null;
  discount_pct: number | null;
  fema_zone: string | null;
  score: number | null;
  classification: "FORTE" | "MODERADO" | "FRACO" | "EVITAR" | null;
  score_breakdown?: ScoreBreakdown;
  ai_analysis?: AiAnalysis | null;
  listing_url: string;
  parcel_id: string | null;
  sale_date: string | null;
  scraped_at: string | null;
  passed_filters: boolean;
  population?: number;
  median_hh_income?: number;
}

export interface PipelineRun {
  id: number;
  status: "rodando" | "concluído" | "erro";
  started_at: string | null;
  finished_at: string | null;
  scraped: number;
  enriched: number;
  filtered: number;
  scored: number;
  error_msg: string | null;
}

export interface PropertyFilters {
  state?: string;
  county?: string;
  classification?: string;
  min_score?: number;
  max_price?: number;
  min_acres?: number;
  max_price_per_acre?: number;
  min_discount_pct?: number;
}
```

- [ ] **Step 2: Update api/properties.ts to send new params**

Replace `frontend/src/api/properties.ts`:
```typescript
import type { Property, PropertyFilters } from "../types";
import client from "./client";

export async function fetchProperties(filters: PropertyFilters = {}): Promise<Property[]> {
  const params: Record<string, string | number> = {};
  if (filters.state) params.state = filters.state;
  if (filters.county) params.county = filters.county;
  if (filters.classification) params.classification = filters.classification;
  if (filters.min_score != null) params.min_score = filters.min_score;
  if (filters.max_price != null) params.max_price = filters.max_price;
  if (filters.min_acres != null) params.min_acres = filters.min_acres;
  if (filters.max_price_per_acre != null) params.max_price_per_acre = filters.max_price_per_acre;
  if (filters.min_discount_pct != null) params.min_discount_pct = filters.min_discount_pct;

  const { data } = await client.get<Property[]>("/properties/", { params });
  return data;
}

export async function fetchProperty(id: number): Promise<Property> {
  const { data } = await client.get<Property>(`/properties/${id}`);
  return data;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/properties.ts
git commit -m "feat: add classification, score_breakdown, county to frontend types and API client"
```

---

## Task 13: Update FilterPanel.tsx

**Files:**
- Modify: `frontend/src/components/FilterPanel.tsx`

- [ ] **Step 1: Replace the component**

```tsx
import type { PropertyFilters } from "../types";

interface Props {
  filters: PropertyFilters;
  onChange: (filters: PropertyFilters) => void;
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  prefix,
  suffix,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
  placeholder: string;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
        {label}
      </label>
      <div
        className="flex items-center gap-1 rounded-lg px-3 py-2"
        style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
      >
        {prefix && <span className="text-sm" style={{ color: "#64748b" }}>{prefix}</span>}
        <input
          type="number"
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm outline-none min-w-0"
          style={{ color: "#e2e8f0" }}
        />
        {suffix && <span className="text-sm" style={{ color: "#64748b" }}>{suffix}</span>}
      </div>
    </div>
  );
}

function SelectFilter({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string | undefined;
  onChange: (v: string | undefined) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
        {label}
      </label>
      <select
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || undefined)}
        className="rounded-lg px-3 py-2 text-sm outline-none"
        style={{ backgroundColor: "#0a0a0f", border: "1px solid #1e1e2e", color: "#e2e8f0" }}
      >
        <option value="">Todos</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}

export default function FilterPanel({ filters, onChange }: Props) {
  return (
    <div
      className="rounded-xl p-4 space-y-4"
      style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
    >
      <h3 className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>Filtros</h3>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <SelectFilter
          label="Estado"
          value={filters.state}
          onChange={(v) => onChange({ ...filters, state: v })}
          options={[{ value: "AL", label: "Alabama" }, { value: "AR", label: "Arkansas" }]}
        />

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "#64748b" }}>
            Condado
          </label>
          <div
            className="flex items-center gap-1 rounded-lg px-3 py-2"
            style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
          >
            <input
              type="text"
              value={filters.county ?? ""}
              onChange={(e) => onChange({ ...filters, county: e.target.value || undefined })}
              placeholder="Jefferson..."
              className="flex-1 bg-transparent text-sm outline-none min-w-0"
              style={{ color: "#e2e8f0" }}
            />
          </div>
        </div>

        <SelectFilter
          label="Classificação"
          value={filters.classification}
          onChange={(v) => onChange({ ...filters, classification: v })}
          options={[
            { value: "FORTE", label: "FORTE" },
            { value: "MODERADO", label: "MODERADO" },
            { value: "FRACO", label: "FRACO" },
            { value: "EVITAR", label: "EVITAR" },
          ]}
        />

        <FilterInput
          label="Score mín."
          value={filters.min_score}
          onChange={(v) => onChange({ ...filters, min_score: v })}
          placeholder="0"
        />
        <FilterInput
          label="Preço máximo"
          value={filters.max_price}
          onChange={(v) => onChange({ ...filters, max_price: v })}
          placeholder="500000"
          prefix="$"
        />
        <FilterInput
          label="Tamanho mín."
          value={filters.min_acres}
          onChange={(v) => onChange({ ...filters, min_acres: v })}
          placeholder="1"
          suffix="ac"
        />
        <FilterInput
          label="Desconto mín."
          value={filters.min_discount_pct}
          onChange={(v) => onChange({ ...filters, min_discount_pct: v })}
          placeholder="50"
          suffix="%"
        />
      </div>

      <div className="flex items-center justify-end pt-1">
        <button
          onClick={() => onChange({})}
          className="text-xs transition-colors hover:opacity-80"
          style={{ color: "#64748b" }}
        >
          Limpar filtros
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FilterPanel.tsx
git commit -m "feat: add Estado/Condado/Classificação/Score filters to FilterPanel"
```

---

## Task 14: Update PropertyTable.tsx

**Files:**
- Modify: `frontend/src/components/PropertyTable.tsx`

- [ ] **Step 1: Replace column definitions**

Replace the `columns` array (lines 23–192) with:
```tsx
const CLASSIFICATION_COLOR: Record<string, { bg: string; text: string }> = {
  FORTE:    { bg: "rgba(34,197,94,0.12)",  text: "#22c55e" },
  MODERADO: { bg: "rgba(251,191,36,0.12)", text: "#f59e0b" },
  FRACO:    { bg: "rgba(100,116,139,0.12)", text: "#64748b" },
  EVITAR:   { bg: "rgba(239,68,68,0.12)",  text: "#ef4444" },
};

const columns: ColumnDef<Property>[] = [
  {
    accessorKey: "score",
    header: "Score",
    cell: ({ getValue }) => <ScoreBadge score={getValue() as number} size="sm" />,
    size: 80,
  },
  {
    accessorKey: "classification",
    header: "Classificação",
    size: 110,
    cell: ({ getValue }) => {
      const val = (getValue() as string | null) ?? "";
      const style = CLASSIFICATION_COLOR[val] ?? { bg: "transparent", text: "#64748b" };
      if (!val) return <span style={{ color: "#64748b" }}>—</span>;
      return (
        <span
          className="px-2 py-0.5 rounded text-xs font-semibold"
          style={{ backgroundColor: style.bg, color: style.text }}
        >
          {val}
        </span>
      );
    },
  },
  {
    accessorKey: "price",
    header: "Lance",
    size: 120,
    cell: ({ getValue }) => (
      <span style={{ color: "#e2e8f0" }}>{formatCurrency(getValue() as number)}</span>
    ),
  },
  {
    accessorKey: "price_per_acre",
    header: "$/Acre",
    size: 110,
    cell: ({ getValue }) => (
      <span style={{ color: "#64748b" }}>{formatCurrency(getValue() as number)}</span>
    ),
  },
  {
    accessorKey: "county",
    header: "Condado",
    size: 130,
    cell: ({ getValue }) => (
      <span style={{ color: "#e2e8f0" }}>{(getValue() as string) || "—"}</span>
    ),
  },
  {
    accessorKey: "population",
    header: "Pop.",
    size: 90,
    cell: ({ getValue }) => {
      const v = getValue() as number | undefined;
      return (
        <span style={{ color: "#64748b" }}>
          {v ? v.toLocaleString("pt-BR") : "—"}
        </span>
      );
    },
  },
  {
    accessorKey: "fema_zone",
    header: "FEMA",
    size: 70,
    cell: ({ getValue }) => {
      const zone = getValue() as string | null;
      return (
        <span
          className="text-xs font-mono font-semibold"
          style={{ color: zone === "X" ? "#22c55e" : zone ? "#f59e0b" : "#64748b" }}
        >
          {zone ?? "—"}
        </span>
      );
    },
  },
  {
    accessorKey: "sale_date",
    header: "Leilão",
    size: 110,
    cell: ({ getValue }) => (
      <span className="font-mono text-xs" style={{ color: "#64748b" }}>
        {formatSaleDate(getValue() as string | null)}
      </span>
    ),
  },
  {
    accessorKey: "state",
    header: "UF",
    size: 55,
    cell: ({ getValue }) => (
      <span className="font-mono text-xs px-1.5 py-0.5 rounded"
        style={{ backgroundColor: "rgba(108,99,255,0.1)", color: "#6c63ff" }}>
        {getValue() as string}
      </span>
    ),
  },
];
```

Remove the import of `VerdictBadge` from line 14 if it's no longer used.
Remove `formatDiscount` from imports if no longer used.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PropertyTable.tsx
git commit -m "feat: update property table — Score/Classificação/Lance/$/Acre/Condado/Pop/FEMA/Leilão"
```

---

## Task 15: Update Dashboard.tsx stats

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace stats calculation and display**

Change lines 32–35 from:
```tsx
const highScore = properties.filter((p) => (p.score ?? 0) >= 70).length;
const midScore = properties.filter(
  (p) => (p.score ?? 0) >= 40 && (p.score ?? 0) < 70
).length;
```
to:
```tsx
const forte = properties.filter((p) => p.classification === "FORTE").length;
const moderado = properties.filter((p) => p.classification === "MODERADO").length;
const fraco = properties.filter(
  (p) => p.classification === "FRACO" || p.classification === "EVITAR"
).length;
```

Change the stats grid from:
```tsx
{ label: "Total", value: properties.length, color: "#e2e8f0" },
{ label: "Score alto (≥70)", value: highScore, color: "#22c55e" },
{ label: "Score médio (40–70)", value: midScore, color: "#f59e0b" },
```
to:
```tsx
{ label: "Total", value: properties.length, color: "#e2e8f0" },
{ label: "FORTE", value: forte, color: "#22c55e" },
{ label: "MODERADO", value: moderado, color: "#f59e0b" },
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: dashboard stats show FORTE/MODERADO counts"
```

---

## Task 16: Update PropertyDetail.tsx

**Files:**
- Modify: `frontend/src/pages/PropertyDetail.tsx`

- [ ] **Step 1: Remove unused imports**

Remove from imports: `Zap`, `Navigation`, `CheckCircle2`, `AlertCircle`

Add to imports: `BarChart2`

Remove `VerdictBadge` import.

- [ ] **Step 2: Add ClassificationBadge helper**

After the `ActionButton` component (line ~97), add:
```tsx
const CLASSIFICATION_STYLE: Record<string, { bg: string; text: string }> = {
  FORTE:    { bg: "rgba(34,197,94,0.15)",  text: "#22c55e" },
  MODERADO: { bg: "rgba(251,191,36,0.15)", text: "#f59e0b" },
  FRACO:    { bg: "rgba(100,116,139,0.15)", text: "#64748b" },
  EVITAR:   { bg: "rgba(239,68,68,0.15)",  text: "#ef4444" },
};

function ClassificationBadge({ classification }: { classification: string | null }) {
  if (!classification) return null;
  const s = CLASSIFICATION_STYLE[classification] ?? { bg: "transparent", text: "#64748b" };
  return (
    <span
      className="px-3 py-1 rounded-full text-sm font-semibold"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      {classification}
    </span>
  );
}
```

- [ ] **Step 3: Update header to show classification**

In the header div (around line 154–171), after `<ScoreBadge score={property.score} size="lg" />`, add:
```tsx
{property.classification && (
  <ClassificationBadge classification={property.classification} />
)}
```

- [ ] **Step 4: Update "Dados Básicos" card — show only non-null fields**

Replace the Dados Básicos motion.div content with conditional rendering:
```tsx
<h2 className="text-sm font-semibold mb-3" style={{ color: "#e2e8f0" }}>Dados Básicos</h2>
{property.price != null && (
  <DataRow icon={DollarSign} label="Lance mínimo" value={formatCurrency(property.price)} />
)}
{property.acres != null && (
  <DataRow icon={Maximize2} label="Tamanho" value={formatAcres(property.acres)} />
)}
{property.price_per_acre != null && (
  <DataRow icon={DollarSign} label="Preço por acre" value={formatCurrency(property.price_per_acre)} />
)}
{property.discount_pct != null && (
  <DataRow
    icon={TrendingDown}
    label="Desconto vs. mercado"
    value={
      <span style={{ color: property.discount_pct >= 50 ? "#22c55e" : "#e2e8f0" }}>
        {formatDiscount(property.discount_pct)}
      </span>
    }
  />
)}
{property.sale_date && (
  <DataRow
    icon={Calendar}
    label="Data do leilão"
    value={<span style={{ color: "#f59e0b" }}>{formatSaleDate(property.sale_date)}</span>}
  />
)}
{property.parcel_id && (
  <DataRow icon={MapPin} label="ID da parcela" value={<span className="font-mono text-xs">{property.parcel_id}</span>} />
)}
<DataRow icon={MapPin} label="Fonte" value={property.source.toUpperCase()} />
```

- [ ] **Step 5: Replace "Localização & Infraestrutura" card with "Mercado & Risco"**

Replace that entire motion.div with:
```tsx
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ delay: 0.2 }}
  className="rounded-xl p-5"
  style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
>
  <h2 className="text-sm font-semibold mb-3" style={{ color: "#e2e8f0" }}>Mercado & Risco</h2>
  {property.fema_zone && (
    <DataRow
      icon={Shield}
      label="Zona FEMA"
      value={
        <span className="font-mono" style={{ color: property.fema_zone === "X" ? "#22c55e" : "#f59e0b" }}>
          {property.fema_zone}
        </span>
      }
    />
  )}
  {property.population != null && (
    <DataRow
      icon={MapPin}
      label="Pop. do condado"
      value={property.population.toLocaleString("pt-BR")}
    />
  )}
  {property.median_hh_income != null && (
    <DataRow
      icon={TrendingDown}
      label="Renda mediana"
      value={new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(property.median_hh_income)}
    />
  )}
  {property.lat != null && property.lng != null && (
    <DataRow
      icon={MapPin}
      label="Coordenadas"
      value={
        <span className="font-mono text-xs" style={{ color: "#64748b" }}>
          {property.lat.toFixed(4)}, {property.lng.toFixed(4)}
        </span>
      }
    />
  )}
</motion.div>
```

- [ ] **Step 6: Add Score Breakdown card**

After the grid div (closing `</div>` after the two cards), add:
```tsx
{property.score_breakdown && (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: 0.22 }}
    className="rounded-xl p-5"
    style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
  >
    <h2 className="text-sm font-semibold mb-4" style={{ color: "#e2e8f0" }}>Score Breakdown</h2>
    <div className="space-y-3">
      {[
        { label: "A — Desconto real", pts: property.score_breakdown.a_pts, max: 50, color: "#6c63ff" },
        { label: "B — Liquidez do mercado", pts: property.score_breakdown.b_pts, max: 35, color: "#22c55e" },
        { label: "C — Risco FEMA", pts: property.score_breakdown.c_pts, max: 15, color: "#f59e0b" },
      ].map(({ label, pts, max, color }) => (
        <div key={label}>
          <div className="flex justify-between text-xs mb-1" style={{ color: "#64748b" }}>
            <span>{label}</span>
            <span style={{ color: "#e2e8f0" }}>{pts} / {max}</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ backgroundColor: "#1e1e2e" }}>
            <div
              className="h-1.5 rounded-full transition-all"
              style={{ width: `${(pts / max) * 100}%`, backgroundColor: color }}
            />
          </div>
        </div>
      ))}
    </div>
  </motion.div>
)}
```

- [ ] **Step 7: Replace "Análise de Investimento" card with AI Analysis (hidden by default)**

Remove the entire "Análise de Investimento" motion.div block (the one with investment_type, risk_level, risk_flags).

Replace the AI Analysis section (the entire `{ai ? (...) : (...)}` block) with:
```tsx
{property.ai_analysis && (
  <motion.div
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: 0.28 }}
    className="rounded-xl p-5 space-y-4"
    style={{ backgroundColor: "#12121a", border: "1px solid #1e1e2e" }}
  >
    <h2 className="text-sm font-semibold" style={{ color: "#64748b" }}>
      Análise Claude AI (opcional)
    </h2>
    <p className="text-sm leading-relaxed" style={{ color: "#64748b" }}>
      {property.ai_analysis.resumo}
    </p>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "#22c55e" }}>
          Pontos positivos
        </p>
        <ul className="space-y-1.5">
          {property.ai_analysis.pontos_positivos.map((p, i) => (
            <li key={i} className="text-sm" style={{ color: "#64748b" }}>· {p}</li>
          ))}
        </ul>
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: "#f59e0b" }}>
          Pontos de atenção
        </p>
        <ul className="space-y-1.5">
          {property.ai_analysis.pontos_atencao.map((p, i) => (
            <li key={i} className="text-sm" style={{ color: "#64748b" }}>· {p}</li>
          ))}
        </ul>
      </div>
    </div>
  </motion.div>
)}
```

Also remove the `const { ai_analysis: ai } = property;` line since we access it directly now.

- [ ] **Step 8: Remove unused imports from PropertyDetail**

Verify and remove: `Zap`, `Navigation`, `CheckCircle2`, `AlertCircle`, `VerdictBadge` if not referenced.
Add `BarChart2` if referenced (else omit).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/pages/PropertyDetail.tsx
git commit -m "feat: property detail — classification badge, score breakdown, only real data, AI hidden"
```

---

## Task 17: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Score and Classifier sections**

In the "Arquitetura" and pipeline sections, update to reflect:
- Score: A(desconto 50) + B(liquidez 35) + C(FEMA 15), sem penalidades
- Classificação: FORTE/MODERADO/FRACO/EVITAR
- Filtros hard: FEMA A/AE/AO/AH/VE/V, pop<2500, acreage<0.10, price<$25, keywords

Update the `## Testes` section to reflect the actual test count post-rewrite.

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with simplified score and classifier system"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Remove AI scorer by default | Task 4 (generate_ai_analysis still exists but AI not called in pipeline unless explicitly added back) |
| Remove has_road_access/utilities from scorer | Task 4 ✓ |
| Remove median×0.15/×0.20 | Task 1 ✓ |
| FEMA A/AE/AO/AH/VE/V → eliminate | Task 3 ✓ |
| acreage < 0.10 → eliminate | Task 3 ✓ |
| price < $25 → eliminate (already in junk filter) | Task 10 — verify existing test |
| Keywords in address | Already in is_junk_property — Task 10 verifies |
| Pop < 2500 → eliminate | Task 3 ✓ |
| Component A: discount 50pts | Task 4 ✓ |
| Component B: pop(20) + income(15) = 35pts | Task 4 ✓ |
| Component C: FEMA 15pts | Task 4 ✓ |
| No negative penalties | Task 4 ✓ |
| FORTE/MODERADO/FRACO/EVITAR classifier | Task 5 ✓ |
| Dashboard: FORTE first | Task 7 (sort) ✓ |
| Dashboard filters: State/County/Classificação/Score | Task 13 ✓ |
| Table columns: Score|Classificação|Lance|$/acre|Condado|Pop|FEMA|Leilão | Task 14 ✓ |
| Detail: score breakdown | Tasks 4+7+16 ✓ |
| Detail: only real data (no empty fields) | Task 16 ✓ |
| Detail: AI hidden by default | Task 16 ✓ |
| Update tests | Tasks 8–10 ✓ |
| Update CLAUDE.md | Task 17 ✓ |

**Gap found:** The pipeline still calls `generate_ai_analysis` on every scored property. The spec says AI should be "disabled by default, manual option". Fix: in Task 4's pipeline.py change, also comment out / remove the `ai_result = await generate_ai_analysis(listing)` block. Add a note in Task 2.

**Fix for gap:** In Task 2, also remove the AI analysis call from `pipeline.py`:
Find and remove (or comment out) lines ~201-203:
```python
ai_result = await generate_ai_analysis(listing)
if ai_result:
    listing["ai_analysis"] = json.dumps(ai_result, ensure_ascii=False)
```

**Type consistency check:** `calculate_score_breakdown` returns `{a_pts, b_pts, c_pts}` (Task 4), used in route (Task 7) as `score_breakdown` field, typed in frontend (Task 12) as `ScoreBreakdown` with same keys. ✓

**Placeholder scan:** No TBDs found. All code blocks are complete. ✓
