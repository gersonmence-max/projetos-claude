---
tags: [investimento, python, fastapi, react, real-estate, alabama, arkansas]
status: ativo
stack: [Python, FastAPI, SQLite, React, Vite, TailwindCSS, FEMA API]
area: investimento
---

# Tax Deed Finder

## Conexoes Reais
- [[EV Viability Finder]] — reutilizou arquitetura Flask+scoring, evoluiu para FastAPI

## Dependencias
- **Depende de:** [[EV Viability Finder]] — arquitetura de scoring foi base

---
## ZONA PRIVADA — Somente Gerson
> Claude nao edita esta secao.

---
## ZONA CLAUDE

### Stack
- Backend: FastAPI + SQLite (porta 8000)
- Frontend: React + Vite + Tailwind (porta 5173)
- APIs: FEMA NFHL (flood, gratis), Alabama ALDOR PDFs, COSL Arkansas

### Score (3 componentes)
| Componente | Peso | O que mede |
|------------|------|-----------|
| A — Desconto/acre | 50pts | Spread valor vs lance |
| B — Liquidez | 35pts | Valor mercado condado |
| C — FEMA | 15pts | Risco alagamento |

Classificacoes: FORTE / MODERADO / FRACO / EVITAR

### Status: 95/95 testes passando

### Decisoes Arquiteturais
| Decisao | Motivo | Descartadas |
|---------|--------|-------------|
| SQLite | Solo, sem multi-tenant | PostgreSQL (overhead) |
| Alabama + Arkansas | Processo acessivel a nao-residentes | Texas/Florida (competitivos) |
| 3 componentes simples | Facil auditar, sem caixa preta | AI scoring complexo |

### Ultima Sessao
- **Data:** —
- **Feito:** —
- **Parou em:** —
- **Proximo:** —

### Melhorias
| Prioridade | Melhoria | Status |
|------------|----------|--------|
| Alta | OCM Regional: 240 chamadas -> 2 por cidade | pendente |
| Alta | Cache SQLite 30 dias | pendente |
| Media | Census API key valida | pendente |
| Media | TomTom Traffic Flow API | pendente |
