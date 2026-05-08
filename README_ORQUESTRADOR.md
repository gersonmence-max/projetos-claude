# 🤖 ORQUESTRADOR MULTIPROJETOS - GUIA DE USO

**Sistema que cria 13 projetos automaticamente, valida internamente, e entrega completos.**

---

## ⚡ INÍCIO RÁPIDO

### Opção 1: Executar via Python

```bash
cd "C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"
python3 orquestrador_multiprojetos.py
```

### Opção 2: Executar via Bash

```bash
cd "C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"
bash executar_orquestrador.sh
```

---

## 📋 O QUE O ORQUESTRADOR FAZ

### ✅ Fase 1: Descoberta Automática
- Escaneia a pasta `projetos-organizados`
- Encontra todos os 13 projetos
- Valida que cada um tem `PROJETO.txt`

### ✅ Fase 2: Processamento Contínuo (SEM PAUSA)
**Para cada projeto (13 vezes):**

1. **Lê PROJETO.txt** (2s)
   - Extrai objetivo, stack, roadmap

2. **Gera especificação customizada** (3s)
   - Adapta para stack técnica do projeto

3. **Executa DEV CREATOR v3** (~18s)
   - Gera código completo
   - Cria arquivos: config.py, models.py, database.py, main.py, etc.

4. **Valida com 8 checkpoints** (~25s)
   - ✅ Arquivos foram criados?
   - ✅ Nenhum está vazio?
   - ✅ Sintaxe Python está correta?
   - ✅ Conteúdo esperado presente?
   - ✅ Imports OK?
   - ✅ Agent revisa qualidade
   - ✅ E2E tests passam?
   - ✅ Relatório gerado?

5. **Gera relatório** (5s)
   - Salva em `projeto_N/reports/validation_report.json`

6. **AVANÇA PARA PRÓXIMO** (⏭️ SEM PAUSA)
   - Continua imediatamente

### ✅ Fase 3: Relatório Consolidado
- Resume os 13 projetos
- Indica sucessos e erros
- Fornece próximas ações

---

## 📊 TEMPO ESTIMADO

| Operação | Tempo |
|----------|-------|
| Por projeto (média) | ~58 segundos |
| Total (13 projetos) | ~10 minutos |
| Incluindo relatórios | ~12 minutos |

---

## 📁 ESTRUTURA DE SAÍDA

```
projetos-organizados/
├── 01-SMB-OS/
│   ├── PROJETO.txt (original)
│   ├── src/ (GERADO)
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── setup.sh
│   │   └── README.md
│   └── reports/ (GERADO)
│       └── validation_report.json
│
├── 02-Mence-Design/
│   ├── src/ (GERADO)
│   └── reports/ (GERADO)
│
... (03 a 13)
│
└── reports_consolidados/
    ├── TODOS_PROJETOS_RESUMO.md ← LEIA ISTO PRIMEIRO
    ├── EXEC_CONSOLIDADO.json
    └── logs/
        └── orquestrador.log
```

---

## 🎯 PRÓXIMAS AÇÕES APÓS CONCLUSÃO

### 1️⃣ Revisar Relatórios (OPCIONAL)

```bash
# Abra este arquivo
notepad "reports_consolidados/TODOS_PROJETOS_RESUMO.md"

# Ou revise com Claude
# Cole o conteúdo em uma conversa Claude e peça análise
```

### 2️⃣ Se Quiser Ajustar Algo

- Abra os arquivos gerados em `projeto_N/src/`
- Solicite a Claude para fazer mudanças
- Código corrigido será gerado

### 3️⃣ Executar os Projetos

```bash
# Para cada projeto
cd projeto_N/src

# Setup inicial
bash setup.sh

# Rodar
python main.py

# Ou deploy (se tiver systemd)
sudo systemctl start projeto_N
```

---

## 🔧 CONFIGURAÇÃO AVANÇADA

Edite `orquestrador_multiprojetos.py` linha ~260:

```python
config = {
    "timeout_por_projeto": 600,      # 10 minutos máximo por projeto
    "max_tentativas_regeneracao": 3, # Quantas vezes regenerar se falhar
    "modo_continuo": True            # False = pausa para revisão (não use!)
}
```

---

## 📝 LOGGING E DEBUG

Os logs estão em:

```
logs/orquestrador.log
```

Para ver em tempo real:

```bash
# Linux/Mac
tail -f logs/orquestrador.log

# Windows
Get-Content logs/orquestrador.log -Wait
```

---

## ⚠️ TROUBLESHOOTING

### ❌ "ModuleNotFoundError: No module named 'something'"

**Solução:** Instale dependências
```bash
pip install -r requirements_orquestrador.txt
```

### ❌ "Permission denied" ao executar script bash

**Solução:** No Windows, use Python diretamente:
```bash
python3 orquestrador_multiprojetos.py
```

### ❌ Um projeto falhou (status: "erro")

**Solução:** 
1. Verifique o relatório: `projeto_N/reports/validation_report.json`
2. Revise `logs/orquestrador.log` para detalhes
3. Se necessário, regenere manualmente:
   ```bash
   cd projeto_N
   rm -rf src/  # Remove código antigo
   python3 orquestrador_multiprojetos.py  # Roda novamente
   ```

---

## 🎨 FLUXOGRAMA DE EXECUÇÃO

```
ENTRADA: "python3 orquestrador_multiprojetos.py"
    ↓
DESCOBRE 13 PROJETOS
    ↓
┌─────────────────────────────────────┐
│ LOOP PARA CADA PROJETO (sem pausa): │
├─────────────────────────────────────┤
│ 1. Lê PROJETO.txt          [2s]     │
│ 2. Gera spec               [3s]     │
│ 3. Executa DEV CREATOR    [18s]     │
│ 4. Valida (8 checkpoints) [25s]     │
│ 5. Gera relatório          [5s]     │
│ 6. PRÓXIMO PROJETO         ⏭️        │
└─────────────────────────────────────┘
    ↓
TODOS 13 PROJETOS COMPLETOS
    ↓
GERA RELATÓRIO CONSOLIDADO
    ↓
✅ SISTEMA PRONTO
    ↓
VOCÊ REVISA (opcional) OU RODA DIRETO
```

---

## 📞 SUPORTE

Se tiver problemas:

1. **Revise o log:** `logs/orquestrador.log`
2. **Abra com Claude:** Cole o erro no chat Claude
3. **Regenere:** Delete a pasta `src/` do projeto e execute novamente

---

## 🎉 RESULTADO ESPERADO

Após ~10-12 minutos:

```
================================================================================
🎉 ORQUESTRADOR FINALIZADO
================================================================================
✅ Completos: 13/13
❌ Com Erro: 0/13
⏱️  Tempo Total: 654.3s (10.9 minutos)
================================================================================
```

**Status:** Todos os 13 projetos criados, validados e prontos para revisão manual (opcional) ou execução direta.

---

**Versão:** 1.0
**Data:** 2026-05-06
**Modo:** Contínuo (sem pausa para revisão manual)
