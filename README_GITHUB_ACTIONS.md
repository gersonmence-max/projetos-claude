# 🤖 GitHub Actions - Orquestrador Automático

Este documento explica como o **Orquestrador de Agentes** funciona automaticamente no GitHub.

---

## ✨ O que está acontecendo:

```
⏰ TODOS OS DIAS às 2AM (horário de Brasília)
  ↓
🚀 GitHub Actions dispara automaticamente
  ↓
📦 Clona o repositório
  ↓
🔍 Descobre TODOS os projetos
  ↓
🤖 Executa 6 AGENTES para cada projeto:
   1. 🔍 Revisor
   2. 🛡️ Segurança Avançado v2
   3. ⚡ Performance
   4. 🏗️ Arquiteto
   5. 💻 Programador
   6. 📊 Consolidador
  ↓
📊 Gera sugestões e relatórios
  ↓
📤 Faz commit automático dos resultados
  ↓
✅ Análise concluída!
```

---

## 🔧 Arquivo do Workflow:

```
.github/workflows/orquestrador-agentes-diario.yml
```

---

## 📋 Detalhes Técnicos:

### **Horário de execução:**
- **Cron:** `0 5 * * *` (5AM UTC = 2AM Brasília)
- **Timezone:** Brasília (UTC-3)
- **Frequência:** Todos os dias

### **Etapas do workflow:**

1. **Clone do repositório**
   - Atualiza código automaticamente

2. **Setup Python 3.11**
   - Instala ambiente Python
   - Carrega dependências (requirements.txt)

3. **Descoberta de projetos**
   - Procura por pastas com `PROJETO.txt`
   - Identifica contexto de cada projeto

4. **Execução dos 6 agentes**
   - Analisa cada projeto
   - Gera sugestões de melhoria

5. **Commit automático**
   - Salva resultados em `sugestoes/`
   - Faz push para GitHub
   - Com retry automático (3 tentativas)

6. **Notificação de conclusão**
   - Gera resumo da execução
   - Registra timestamp

---

## 📂 Estrutura de saída:

```
sugestoes/
├── Nome-do-Projeto-1/
│   └── Nome-do-Projeto-1_sugestoes_20260507_020000.txt
├── Nome-do-Projeto-2/
│   └── Nome-do-Projeto-2_sugestoes_20260507_020000.txt
└── ...
```

---

## 🔍 Como acompanhar as execuções:

### **GitHub Web:**
1. Vá para seu repositório
2. Clique em **"Actions"** (aba superior)
3. Veja todas as execuções do workflow
4. Clique em qualquer execução para ver detalhes

### **Ver logs:**
- Clique na execução específica
- Veja cada step em tempo real
- Identifique erros ou alertas

### **Histórico:**
- Todas as execuções são mantidas
- Pode-se rastrear quando rodou
- Compara resultados ao longo do tempo

---

## ✅ O que o workflow garante:

```
✅ Roda EXATAMENTE 2AM todo dia
✅ SEM necessidade de você fazer nada
✅ Descobre projetos novos automaticamente
✅ Avalia com 6 agentes especializados
✅ Salva sugestões no Git
✅ Retry automático se falhar
✅ Historicamente rastreado
✅ Zero custo (GitHub Actions é gratuito)
```

---

## 🚨 Se houver erro:

1. **Verifique Actions → Workflow runs**
2. **Clique na execução com erro**
3. **Veja logs detalhados**
4. **Problemas comuns:**
   - ❌ `requirements.txt` com versões incompatíveis
   - ❌ Projeto sem `PROJETO.txt`
   - ❌ Erro de push (conflict)

---

## 🔐 Permissões necessárias:

O workflow usa `${{ secrets.GITHUB_TOKEN }}` que:
- ✅ É fornecido automaticamente pelo GitHub
- ✅ Permite fazer commit
- ✅ Permite fazer push
- ✅ Expires automaticamente após cada run

**Sem necessidade de tokens manuais!**

---

## 📊 Exemplo de execução bem-sucedida:

```
✅ Workflow: Orquestrador de Agentes - Análise Automática 2AM
📅 Rodou: 2026-05-07 02:00:15 (Brasília)
⏱️ Duração: 12 minutos

Steps:
  ✅ Clonar repositório (2s)
  ✅ Configurar Python 3.11 (15s)
  ✅ Instalar dependências (30s)
  ✅ Descobrir projetos (5s)
  ✅ Executar 6 agentes (8m 45s)
  ✅ Fazer commit (1m 20s)
  ✅ Resumo da execução (5s)

📊 Resultados:
  • 13 projetos analisados
  • 6 agentes × 13 projetos = 78 análises
  • 47 sugestões geradas
  • 3 commits feitos

✅ SUCESSO! Análise salva em sugestoes/
```

---

## 🎯 Próximos passos:

1. **Confirmar funcionamento:**
   - Vá em Actions no GitHub
   - Veja se o workflow rodou no horário esperado

2. **Acompanhar resultados:**
   - Verifique `sugestoes/` para ver análises
   - Revise sugestões geradas pelos agentes

3. **Customizar (opcional):**
   - Ajuste horário em `.github/workflows/orquestrador-agentes-diario.yml`
   - Mude cron expression: `cron: 'minutos horas * * *'`

---

## 🚀 Exemplo: Mudar horário

Edite o arquivo `.github/workflows/orquestrador-agentes-diario.yml`:

```yaml
on:
  schedule:
    # De 2AM (5AM UTC) para 10AM (1PM UTC)
    - cron: '0 13 * * *'  # ← Mude aqui
```

---

## 📞 Monitoramento contínuo:

GitHub Actions fornece:
- ✅ Histórico completo de execuções
- ✅ Notificações automáticas de falha
- ✅ Logs detalhados de cada step
- ✅ Timing e performance tracking
- ✅ Status badge que pode ser exibido

---

**🎉 Seu orquestrador está funcionando 24/7 no GitHub! 🎉**

A partir de agora, **TODAS as noites às 2AM**, os 6 agentes analisarão automaticamente todos os seus projetos e gerarão sugestões de melhoria!

