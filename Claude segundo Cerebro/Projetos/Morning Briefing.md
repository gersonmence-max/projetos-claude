---
tags: [automacao, python, telegram, gemini]
status: ativo
stack: [Python, Gemini 2.0 Flash, gTTS, Telegram, Gmail API, Google Calendar, yfinance]
area: automacao
---

# Morning Briefing

## Conexoes Reais
- [[Ziontec Bot]] — reutiliza estrutura de bot Telegram

## Dependencias
- **Depende de:** [[Ziontec Bot]] — pipeline Telegram e estrutura de bot.py foram base

---
## ZONA PRIVADA — Somente Gerson
> Claude nao edita esta secao.

---
## ZONA CLAUDE

### Stack
- Python puro (sem CrewAI/Smolagents)
- LLM: Gemini 2.0 Flash (gratis)
- TTS: gTTS (gratis)
- Dados: Gmail + Google Calendar + yfinance + RSS

### 5 Agentes
1. Reporter — RSS G1/BBC/Reuters, resume PT-BR
2. Analista — BTC + Ouro + B3 + S&P + cambio
3. Assistente — Gmail urgente + Calendar do dia
4. Locutor — monta roteiro podcast
5. Produtor — converte .mp3, envia Telegram

### Decisoes Arquiteturais
| Decisao | Motivo | Descartadas |
|---------|--------|-------------|
| Python puro | CrewAI quebra facil | CrewAI, Smolagents |
| Gemini 2.0 Flash | Gratis, cota generosa | Claude Haiku (pago) |
| gTTS | Gratis, suficiente | ElevenLabs (pago) |

### Ultima Sessao
- **Data:** —
- **Feito:** —
- **Parou em:** —
- **Proximo:** Configurar como servico no VPS Hetzner

### Melhorias
| Prioridade | Melhoria | Status |
|------------|----------|--------|
| Alta | Configurar servico VPS 24/7 | pendente |
| Media | Resumo emails Slack/WhatsApp | pendente |
| Baixa | Voz ElevenLabs | pendente |
