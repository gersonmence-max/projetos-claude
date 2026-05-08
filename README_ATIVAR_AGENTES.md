# ⏰ ATIVAR SCHEDULER COM 6 AGENTES

**Sistema automático que roda às 2AM todos os dias com agentes especializados**

---

## 🚀 INÍCIO RÁPIDO (2 CLIQUES)

### Windows

1. **Abra:** `ativar_scheduler_agentes.bat`
2. **Escolha opção 1** → Scheduler inicia
3. **Deixe rodando** ✅

---

## 📖 OPÇÕES DO MENU

```
1. Iniciar scheduler COM AGENTES (recomendado)
   └─ Roda às 2AM todos os dias
   └─ 6 agentes analisam projetos
   └─ Deixe terminal aberto

2. Executar análise COM AGENTES AGORA
   └─ Testa os agentes imediatamente
   └─ Sem esperar 2AM

3. Executar análise SIMPLES AGORA
   └─ Versão rápida (sem agentes)
   └─ Apenas analisador

4. Ver logs
   └─ Mostra últimas execuções
   └─ Útil para debug

5. Parar scheduler
   └─ Fechar terminal
```

---

## 🤖 OS 6 AGENTES

Quando você escolhe opção 1 ou 2, executa:

```
🔍 REVISOR
   └─ Qualidade, padrões, boas práticas

🛡️ SEGURANÇA
   └─ SQL injection, XSS, vulnerabilidades

⚡ PERFORMANCE
   └─ N+1 queries, cache, otimizações

🏗️ ARQUITETO
   └─ Design patterns, escalabilidade

💻 PROGRAMADOR
   └─ Gera código pronto para usar

📊 CONSOLIDADOR
   └─ Agrega análises, prioriza
```

---

## 📊 FLUXO

```
02:00 (2AM automaticamente)
    ↓
INICIA SCHEDULER COM AGENTES
    ↓
6 AGENTES ANALISAM TODOS OS PROJETOS
    ├─ 🔍 REVISOR
    ├─ 🛡️ SEGURANÇA
    ├─ ⚡ PERFORMANCE
    ├─ 🏗️ ARQUITETO
    ├─ 💻 PROGRAMADOR
    └─ 📊 CONSOLIDADOR
    ↓
GERA RELATÓRIOS EM: sugestoes/
    ├─ INDICE.txt (resumo)
    ├─ 01-SMB-OS.txt
    ├─ 02-Mence-Design.txt
    ... (todos os projetos)
    ↓
VOCÊ ACORDA
    ↓
LÊ sugestoes/INDICE.txt
    ↓
VÊ ANÁLISES DE 6 AGENTES
    ↓
APROVA OU REJEITA
```

---

## 📝 EXEMPLO DE SAÍDA

```
sugestoes/01-SMB-OS.txt:

════════════════════════════════════════════════════════════════════════════════
📋 ANÁLISE POR AGENTES ESPECIALIZADOS - 01-SMB-OS
════════════════════════════════════════════════════════════════════════════════

Analisado: 2026-05-08 02:00
Agentes Envolvidos: 6

════════════════════════════════════════════════════════════════════════════════
AGENTES QUE ANALISARAM
════════════════════════════════════════════════════════════════════════════════

✅ 🔍 AGENTE REVISOR
   Responsável por: Qualidade, padrões, boas práticas
   Status: Análise concluída

✅ 🛡️ AGENTE SEGURANÇA
   Responsável por: Vulnerabilidades, autenticação, proteção
   Status: Análise concluída
   Achado: 🔴 CRÍTICO - SQL Injection

✅ ⚡ AGENTE PERFORMANCE
   Responsável por: Gargalos, otimizações, escalabilidade
   Status: Análise concluída
   Achado: 🔴 CRÍTICO - N+1 Query (100x lento)

✅ 🏗️ AGENTE ARQUITETO
   Responsável por: Design patterns, arquitetura, manutenibilidade
   Status: Análise concluída

✅ 💻 AGENTE PROGRAMADOR
   Responsável por: Implementação, código, testes
   Status: Pronto para implementar sugestões críticas
   Código Pronto: SIM (para 4 sugestões)

✅ 📊 AGENTE CONSOLIDADOR
   Responsável por: Agregar análises, priorizar, exportar
   Status: Relatório consolidado gerado

════════════════════════════════════════════════════════════════════════════════
```

---

## ⏰ HORÁRIOS

### 2AM é melhor porque:
- ✅ Menos uso de recursos
- ✅ Você dorme (não atrapalha)
- ✅ Análise pronta ao acordar
- ✅ Relatórios frescos no café ☕

### Mudar horário:
Edite `scheduler_agentes_diario.py` linha ~80:

```python
# Mude "02:00" para outro horário (formato 24h)
schedule.every().day.at("02:00").do(executar_analise_com_agentes)
```

Exemplos:
- `"01:00"` → 1AM
- `"03:00"` → 3AM
- `"14:00"` → 2PM
- `"23:00"` → 11PM

---

## 🖥️ ATIVAR NO WINDOWS (PERMANENTE)

Se quiser rodar em background permanentemente (sem deixar terminal aberto):

### Task Scheduler (Recomendado)

1. Abra: `taskschd.msc`
2. "Create Basic Task..."
3. Nome: `Analise Diaria com Agentes`
4. Trigger: Daily @ 02:00
5. Action: `python scheduler_agentes_diario.py`
6. OK

Ver mais detalhes em: `README_SCHEDULER.md`

---

## 📋 COMPARAÇÃO: SEM vs COM AGENTES

### SEM AGENTES (Rápido)
```
- 1 analisador
- 1 perspectiva
- ~15 segundos
- Sugestões genéricas
```

### COM AGENTES (Robusto)
```
- 6 agentes especializados
- 6 perspectivas diferentes
- ~30 segundos
- Código gerado
- Priorização inteligente
- Análise profunda
```

---

## 🎯 WORKFLOW DIÁRIO

### Noite (02:00)
```
Sistema executa automaticamente:
├─ Scheduler inicia
├─ Orquestrador invoca 6 agentes
├─ Cada agente analisa sua área
├─ Consolidador agrega
└─ TXTs salvos em sugestoes/
```

### Manhã (ao acordar)
```
Você faz:
├─ cat sugestoes/INDICE.txt
├─ Lê resumo de todos projetos
├─ Lê análises de 6 agentes
├─ Aprova sugestões com Claude
└─ Implementa código gerado
```

### Próxima Noite (02:00)
```
Sistema executa novamente:
├─ Analisa código ATUALIZADO
├─ Gera NOVAS sugestões
├─ Melhoria contínua
└─ Ciclo repetido
```

---

## 💡 DICAS

### Teste antes de ativar permanente
```bash
# Opção 2 do menu: executa AGORA
# Assim vê se funciona antes de agendar
```

### Ver logs
```bash
# Opção 4 do menu
# Vê últimas 50 linhas do log
```

### Testar versão simples (sem agentes)
```bash
# Opção 3 do menu
# Mais rápido, sem 6 agentes
```

---

## ⚙️ CONFIGURAÇÃO AVANÇADA

### Múltiplas análises por dia

Edite `scheduler_agentes_diario.py`:

```python
# Análise às 2AM e às 2PM
schedule.every().day.at("02:00").do(executar_analise_com_agentes)
schedule.every().day.at("14:00").do(executar_analise_com_agentes)
```

### Análise a cada X horas

```python
# A cada 12 horas
schedule.every(12).hours.do(executar_analise_com_agentes)
```

---

## 📊 TEMPO DE EXECUÇÃO

| Análise | Tempo |
|---------|-------|
| Simples (sem agentes) | ~15s |
| Com 6 agentes | ~30s |
| 13 projetos | ~30s |
| 50 projetos | ~2 min |
| 100 projetos | ~4 min |

---

## 🆘 TROUBLESHOOTING

### "Python não encontrado"
```
Instale Python 3.9+:
https://www.python.org/downloads/
Marque: "Add Python to PATH"
```

### "Schedule module not found"
```
pip install schedule
```

### Terminal fica preto sem fazer nada
```
Isto é normal! Está aguardando 02:00
Deixe aberto ou use Task Scheduler para permanente
```

### Ver se está rodando
```
# Opção 4 do menu
# Vê logs das últimas execuções
```

---

## ✨ RESULTADO ESPERADO

✅ **Todas as noites às 2AM**
✅ **6 agentes analisam código**
✅ **Relatórios gerados automaticamente**
✅ **Você aprova quando acordar**
✅ **Código melhora continuamente**

---

## 🎉 VOCÊ ESTÁ PRONTO!

1. Execute: `ativar_scheduler_agentes.bat`
2. Escolha opção 1
3. Deixe rodando
4. Amanhã de manhã → `sugestoes/INDICE.txt`
5. Aprove sugestões com Claude
6. Próxima noite → novas sugestões

---

**Sistema robusto com 6 agentes - ATIVO! 🤖**
