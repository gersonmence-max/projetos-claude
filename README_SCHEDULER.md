# ⏰ SCHEDULER DE ANÁLISE DIÁRIA

**Executa análise de sugestões AUTOMATICAMENTE às 2AM todos os dias**

---

## 🚀 INÍCIO RÁPIDO

### Opção 1: Executar via Script Batch (Mais Fácil)

1. **Abra o arquivo:**
   ```
   ativar_scheduler.bat
   ```

2. **Escolha opção 1** para iniciar scheduler

3. **Deixe rodando** (em background ou em terminal)

---

### Opção 2: Executar via Python (Direto)

```bash
cd "C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"
python3 scheduler_analise_diaria.py
```

Escolha opção 1 no menu.

---

## 📋 COMO FUNCIONA

```
Sistema inicia às 2AM (02:00)
    ↓
Descobre todos os projetos
    ↓
Executa analisador_sugestoes.py
    ↓
Gera/atualiza arquivos TXT em sugestoes/
    ↓
Continua rodando até próximo dia
    ↓
Repete todos os dias automaticamente
```

---

## ⏰ CONFIGURAÇÃO: 2AM

Se quiser mudar o horário, edite `scheduler_analise_diaria.py` linha ~115:

```python
# Mude "02:00" para outro horário (24h)
schedule.every().day.at("02:00").do(executar_analise_diaria)
```

Exemplos:
- `"01:00"` → 1AM
- `"03:00"` → 3AM
- `"14:00"` → 2PM
- `"23:30"` → 11:30PM

---

## 🖥️ ATIVAR NO WINDOWS (PERMANENTE)

### Método 1: Task Scheduler (Recomendado)

1. **Abra Task Scheduler:**
   - Pressione `Win+R`
   - Digite: `taskschd.msc`
   - Pressione Enter

2. **Criar nova tarefa:**
   - Clique: "Create Basic Task..."
   - Nome: `Analise Diaria Projetos`
   - Descrição: `Executa análise de sugestões às 2AM`
   - Próximo

3. **Trigger (Quando executar):**
   - Selecione: "Daily"
   - Hora: `02:00`
   - Próximo

4. **Action (O que fazer):**
   - Selecione: "Start a program"
   - Program: `python`
   - Arguments: `C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados\scheduler_analise_diaria.py`
   - Próximo

5. **Finish:**
   - Marque: "Open the Properties dialog..."
   - Clique: "Finish"

6. **Na janela Properties:**
   - Abra aba: "General"
   - Marque: "Run whether user is logged in or not"
   - Marque: "Run with highest privileges"
   - Clique: "OK"

### Método 2: Script PowerShell (Automático)

```powershell
# Abra PowerShell como Administrator
# Cole este código:

$scriptPath = "C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados\scheduler_analise_diaria.py"
$pythonPath = "python"
$taskName = "Analise Diaria Projetos"

# Criar trigger
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# Criar ação
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument $scriptPath

# Criar tarefa
Register-ScheduledTask -TaskName $taskName `
    -Trigger $trigger `
    -Action $action `
    -RunLevel Highest `
    -Force

Write-Host "✅ Tarefa criada: $taskName"
```

---

## 🐧 ATIVAR NO LINUX/MAC

### Usando crontab

```bash
# Abra editor cron
crontab -e

# Adicione esta linha (executa às 2AM todos os dias)
0 2 * * * cd /home/usuario/Projetos\ Claude/projetos-organizados && python3 analisador_sugestoes.py >> logs_scheduler/cron.log 2>&1

# Salve e feche
```

---

## 📊 VERIFICAR LOGS

Os logs são salvos em:
```
logs_scheduler/scheduler_analise.log
```

Para ver:
```bash
# Últimas 50 linhas
tail -50 logs_scheduler/scheduler_analise.log

# Ou abra em editor
code logs_scheduler/scheduler_analise.log
```

---

## 📝 FLUXO DIÁRIO

### Dia 1 (primeira execução)

```
02:00 - Análise inicia
02:15 - 13 projetos analisados
02:15 - Gera arquivo: sugestoes/INDICE.txt
02:15 - Gera arquivos individuais
02:15 - Análise completa

Você acorda →
       Lê arquivo sugestoes/INDICE.txt
       Lê sugestões de projetos
       Aprova algumas (com Claude)
```

### Dia 2 (próxima execução)

```
02:00 - Análise inicia NOVAMENTE
02:15 - Gera NOVO arquivo com sugestões atualizadas
02:15 - Arquivo anterior é SOBRESCRITO

Você acorda →
       Lê arquivo ATUALIZADO
       Novas sugestões (ou mesmas se nada mudou)
```

### Dia N (quando tiver lido tudo)

```
Quando tiver lido e aprovado/rejeitado todas as sugestões:
- Sistema continua rodando
- Gera novos TXTs com melhorias mais recentes
- Você nunca fica sem sugestões para melhorar
```

---

## 🎯 OPÇÕES DO MENU

Ao executar `ativar_scheduler.bat` ou `scheduler_analise_diaria.py`:

### Opção 1: Iniciar Scheduler
```
Inicia loop infinito que executa análise às 2AM
Deixa rodando em background
Executa todo dia automaticamente
```

### Opção 2: Executar Análise AGORA
```
Executa análise imediatamente (para testes)
Útil para verificar se está funcionando
Não aguarda 2AM
```

### Opção 3: Ver Logs
```
Mostra últimas linhas do log
Útil para debug
```

---

## ⚙️ CONFIGURAÇÃO AVANÇADA

### Mudar horário de execução

Edite `scheduler_analise_diaria.py` linha ~115:

```python
# Mude para qualquer horário (24h)
schedule.every().day.at("HH:MM").do(executar_analise_diaria)
```

### Executar múltiplas vezes por dia

```python
# Às 2AM e às 2PM
schedule.every().day.at("02:00").do(executar_analise_diaria)
schedule.every().day.at("14:00").do(executar_analise_diaria)
```

### Executar a cada X horas

```python
# A cada 12 horas
schedule.every(12).hours.do(executar_analise_diaria)
```

---

## 📊 RESULTADO ESPERADO

```
logs_scheduler/scheduler_analise.log:

[2026-05-08 02:00:00] INFO     | ⏰ INICIANDO ANÁLISE DIÁRIA DE SUGESTÕES
[2026-05-08 02:00:00] INFO     | 🔍 01-SMB-OS.......................... 3 sugestões
[2026-05-08 02:00:01] INFO     | 🔍 02-Mence-Design................... 2 sugestões
[2026-05-08 02:00:02] INFO     | 🔍 03-Morning-Briefing.............. ✅ OK
... (continua para todos os projetos)
[2026-05-08 02:00:15] INFO     | ✅ ANÁLISE DIÁRIA CONCLUÍDA COM SUCESSO
[2026-05-08 02:00:15] INFO     | 📊 Projetos analisados: 13
[2026-05-08 02:00:15] INFO     | 📝 Sugestões geradas: 16
```

---

## 🆘 TROUBLESHOOTING

### "Python não encontrado"

```bash
# Instale Python de: https://www.python.org/downloads/
# Marque: "Add Python to PATH"
```

### "Schedule module not found"

```bash
# Instale dependência
pip install schedule
```

### Tarefa não executa no Windows

1. Abra Task Scheduler
2. Procure por: "Analise Diaria Projetos"
3. Clique direito → Properties
4. Abra aba: "General"
5. Marque: "Run whether user is logged in or not"
6. Clique: "OK"

### Ver se tarefa já foi executada

1. Abra Task Scheduler
2. Procure por: "Analise Diaria Projetos"
3. Abra aba: "History"
4. Veja últimas execuções

---

## ✨ RESULTADO FINAL

✅ **Análise automática às 2AM**
✅ **Todos os dias, sem falha**
✅ **Arquivos TXT sempre atualizados**
✅ **Você lê quando acordar**
✅ **Sistema continua gerando sugestões**

---

## 📞 SUPORTE

Se não funcionar:
1. Verifique: `logs_scheduler/scheduler_analise.log`
2. Cole o erro com Claude
3. Claude ajuda a resolver

---

**Status: SCHEDULER COMPLETO E PRONTO**
