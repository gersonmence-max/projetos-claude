# Design: Sistema de Score para Potencial de Revenda

**Data:** 2026-04-14  
**Objetivo:** Filtrar e classificar terrenos tax-deed com potencial real de revenda, eliminando ruído e estimativas sem dados reais.

---

## 1. Filtros de Eliminação (`filters.py`)

Aplicados antes do score. Propriedades eliminadas não aparecem no dashboard (`passed_filters = False`).

| Critério | Valor |
|---|---|
| FEMA zone | A, AE, AO, AH, VE, V → eliminar |
| Acreage | < 0.10 acres → eliminar |
| Preço | < $25 → eliminar (taxa administrativa) |
| Palavras no endereço | right-of-way, easement, drainage, alley, canal, ROW, railroad, pipeline → eliminar |
| População do condado | < 2.500 → eliminar (mercado inexistente) |

Palavras-chave já parcialmente cobertas — expandir para incluir: `AO`, `AH` no filtro FEMA e `0.10` no limite de acreage.

---

## 2. Score Simplificado (`scorer.py`)

**Score final = A + B + C (máximo 100). Sem penalidades negativas.**

### Componente A — Desconto real (50 pts)

**Com acreage disponível:**
```
market_price_per_acre = median_home_value_county  (valor bruto Redfin/Census, sem multiplicador)
discount = (1 - (face_value / acreage) / market_price_per_acre) * 100
pts = min(discount / 80 * 50, 50)
```

**Sem acreage:**
```
pts = min((1 - face_value / median_home_value_county) / 0.8 * 50, 50)
```

Se `discount <= 0` ou dados insuficientes → 0 pts neste componente.

### Componente B — Liquidez do mercado (35 pts)

**População (20 pts):**
- >= 50.000 → 20 pts
- 10.000–50.000 → escala linear: `(pop - 10000) / 40000 * 20`
- 2.500–10.000 → escala linear máx 8 pts: `(pop - 2500) / 7500 * 8`
- < 2.500 → eliminado antes

**Renda mediana familiar (15 pts):**
- >= $55.000 → 15 pts
- $35.000–$55.000 → escala linear: `(income - 35000) / 20000 * 15`
- $25.000–$35.000 → escala linear máx 5 pts: `(income - 25000) / 10000 * 5`
- < $25.000 → 0 pts

### Componente C — Risco FEMA (15 pts)

| Zona | Pontos |
|---|---|
| X | 15 |
| X500 ou B | 10 |
| C | 7 |
| Sem dado | 5 (neutro) |
| A, AE (chegou até aqui) | 0 |

---

## 3. Classificação (`classifier.py`)

Substitui `flip/buy_hold/avoid` por `FORTE/MODERADO/FRACO/EVITAR`.

**FORTE** (score >= 75):
- FEMA zona X ou X500
- população >= 15.000
- desconto >= 50%
- Todos os 3 critérios obrigatórios

**MODERADO** (score 55–74):
- Pelo menos 2 dos 3 critérios do FORTE

**EVITAR:**
- FEMA zona A/AE com score < 65
- OU população < 5.000 com score < 70

**FRACO** (demais, score < 55):
- Mostra mas sinaliza como baixa prioridade

Campo DB: `classification` (string — "FORTE", "MODERADO", "FRACO", "EVITAR").

---

## 4. Modelo de Dados (`models.py`)

- **Adicionar:** `classification` (String, nullable)
- **Manter colunas** `has_road_access`, `utilities_available` no DB (não quebrar schema existente), mas **não usar** no score nem mostrar no frontend
- **Manter** `ai_analysis` no DB, mas ocultar por padrão no frontend
- **Campo `avg_price_per_acre`:** mantém no DB, mas não é mais o input principal do score — `price_per_acre` (face_value/acres) é o que conta

---

## 5. Enriquecedor de Mercado (`zillow_market.py`)

- Remover `_LAND_FRACTION = 0.15` e `_LAND_FRACTION_CENSUS = 0.20`
- Expor função `get_median_home_value(county, state) -> Optional[float]` retornando o valor bruto mediano
- Manter cache existente

---

## 6. Dashboard (frontend)

**Ordenação padrão:** FORTE → MODERADO → FRACO → EVITAR

**Colunas da tabela:**
`Score | Classificação | Lance | $/acre | Condado | Pop. | FEMA | Data leilão`

**Remover da tabela:** Tipo (flip/hold), Risco (low/medium/high), Veredicto AI, Endereço completo (mover pra detail)

**Filtros rápidos:** Estado / Condado / Classificação / Score mínimo

**Substituir** `PropertyFilters` interface para incluir `classification?: string`.

---

## 7. Página de Detalhe (frontend)

Mostrar apenas dados confirmados. Se campo nulo → não renderiza o `DataRow`.

**Seções:**
1. Header: endereço, condado/estado, score badge, classificação badge
2. Ações: Google Maps (lat/lon se disponível, senão endereço), Street View, Link fonte
3. Dados básicos: preço, acres, $/acre, desconto%, data leilão, parcel_id, fonte
4. FEMA + Mercado: zona FEMA, pop. do condado, renda mediana
5. Score breakdown: barra A + B + C com pontuação de cada componente
6. AI Analysis: oculto por padrão, botão "Ver análise Claude" expande (se disponível)

**Remover:** has_road_access, utilities_available, zoning, risk_flags, risk_level, investment_type

---

## 8. Testes

Reescrever `test_scorer.py` e `test_classifier.py` para os novos critérios.
Atualizar `test_filters.py` para incluir AO, AH, acreage=0.10, pop <2500.
Remover testes de `has_road_access` e `utilities_available` do scorer.

Meta: todos os testes passando após a implementação.

---

## Decisões Tomadas

- **Sem acreage no desconto:** usa valor bruto mediano de imóvel (Redfin/Census) sem multiplicador ×0.15/×0.20 (opção B confirmada pelo usuário)
- **A/AE no score:** tratados com 0 pts no componente C (defensivo, caso filtro seja desabilitado ou dados cheguem tarde)
- **Colunas DB:** `has_road_access`, `utilities_available` mantidas no schema para não quebrar DB existente
- **AI Analysis:** mantida no DB e na API, mas oculta por padrão no frontend
