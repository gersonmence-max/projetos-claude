---
tags: [ziontec, python, telegram, automacao]
status: ativo
stack: [Python, Telegram, Google Sheets, Claude Haiku, Groq]
area: ziontec
---

# Ziontec Bot

## Conexoes Reais
- [[Morning Briefing]] — compartilha pipeline Telegram
- [[SMB OS]] — logica operacional aqui vira modulo do SaaS

## Dependencias
- **Alimenta:** [[SMB OS]] — piloto da logica de gestao

---
## ZONA PRIVADA — Somente Gerson
> Claude nao edita esta secao.

---
## ZONA CLAUDE

### Stack
- Python + python-telegram-bot
- LLM: Claude Haiku (primario) + Groq (fallback)
- DB: Google Sheets (intencional — transparencia pro cliente)
- Agendador: APScheduler

### Arquivos
- core.py — logica deterministica, 108 testes
- bot.py — integracao Telegram + Google
- tests_scenarios.py — 108 testes obrigatorios antes de deploy

### Decisoes Arquiteturais
| Decisao | Motivo | Descartadas |
|---------|--------|-------------|
| Google Sheets como DB | Cliente ve os dados direto | PostgreSQL (opaco) |
| core.py separado de bot.py | Isolar logica de integracoes | Arquivo unico |
| Claude Haiku principal | Custo baixo | GPT-4 (caro) |

### Ultima Sessao
- **Data:** —
- **Feito:** —
- **Parou em:** —
- **Proximo:** —

### Melhorias
| Prioridade | Melhoria | Status |
|------------|----------|--------|
| Alta | Bilingual PT/EN | pendente |
| Alta | GPS tracking funcionarios | pendente |
| Media | SaaS publico $19.90/mes | pendente |
