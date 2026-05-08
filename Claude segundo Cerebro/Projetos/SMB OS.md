---
tags: [saas, python, fastapi, postgresql, react, multitenant]
status: ativo
stack: [FastAPI, Next.js, PostgreSQL, Supabase, Expo, Railway, Stripe]
area: saas
---

# SMB OS

## Conexoes Reais
- [[Ziontec Bot]] — logica operacional pilotada aqui
- [[Maria Madah]] — pode ser cliente piloto do modulo ecommerce

## Dependencias
- **Depende de:** [[Ziontec Bot]] — logica de gestao vem daqui

---
## ZONA PRIVADA — Somente Gerson
> Claude nao edita esta secao.

---
## ZONA CLAUDE

### Stack
- Backend: FastAPI + Python
- Frontend: Next.js + TypeScript + Tailwind
- Mobile: Expo
- DB: PostgreSQL via Supabase (multi-tenant RLS)
- Infra: Railway + Vercel
- Pagamentos: Stripe + Plaid

### Decisoes Arquiteturais
| Decisao | Motivo | Descartadas |
|---------|--------|-------------|
| Multi-tenant PostgreSQL RLS | Escala 100+ clientes custo fixo | VM por cliente (insustentavel) |
| Railway pra comecar | Simples, deploy automatico | AWS/GCP (complexidade prematura) |
| Piloto joalheria | Gap real em terceirizacao ourives | Construcao (mercado saturado) |

### Precos
| Plano | Setup | Mensal |
|-------|-------|--------|
| Starter | R$497 | R$397 |
| Pro | R$997 | R$697 |
| Enterprise | R$1.997 | R$1.197 |

### Ultima Sessao
- **Data:** —
- **Feito:** —
- **Parou em:** —
- **Proximo:** Sessao 1 — setup monorepo Next.js + FastAPI + Supabase

### Melhorias
| Prioridade | Melhoria | Status |
|------------|----------|--------|
| Alta | Setup monorepo + banco (Sessao 1) | pendente |
| Alta | Modulo OS restauro + CRM (Sessao 2-3) | pendente |
| Media | App mobile Expo | pendente |
