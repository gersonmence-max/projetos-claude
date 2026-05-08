---
tags: [ziontec, python, flask, react, ev-charging, massachusetts]
status: pausado
stack: [Python, Flask, React, LocationIQ, TomTom, OCM, Google Places]
area: ziontec
---

# EV Viability Finder

## Conexoes Reais
- [[Tax Deed Finder]] — arquitetura de scoring e Flask foi base para o Tax Deed

## Dependencias
- **Alimenta:** [[Tax Deed Finder]] — padrao Flask+scoring foi copiado e melhorado

---
## ZONA PRIVADA — Somente Gerson
> Claude nao edita esta secao.

---
## ZONA CLAUDE

### Stack
- Backend: Python + Flask (porta 5000)
- Frontend: React + Vite + Tailwind (porta 5173)
- 341 cidades de Massachusetts
- APIs: LocationIQ, TomTom, OCM, Google Places

### Pipeline 5 Agentes
1. Geocoding (LocationIQ -> OpenCage -> Nominatim)
2. LocalSearch (Google Places)
3. Viability (TomTom + OCM)
4. Scoring (demand, competition, site_fit, ev_affinity)
5. Ranking (Top 20 por cidade)

### Pendencias Conhecidas
- OCM: 240 chamadas individuais (ineficiente)
- Census API key invalida
- TomTom chamada A->A inutil

### Ultima Sessao
- **Data:** —
- **Feito:** —
- **Parou em:** —
- **Proximo:** Resolver pendencias OCM + Census

### Melhorias
| Prioridade | Melhoria | Status |
|------------|----------|--------|
| Alta | Pendencias tecnicas OCM + Census + TomTom | pendente |
| Media | Cache SQLite 30 dias | pendente |
| Baixa | Expandir outros estados | pendente |
