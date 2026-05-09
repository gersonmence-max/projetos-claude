# Design: Pipeline Gemini (arquiteto) + Groq (gerador) — SMB-OS Build

**Data:** 2026-05-08  
**Projeto:** SMB-OS — `.github/scripts/build_smb_os.py`  
**Status:** Aprovado para implementação

---

## Contexto

O script atual (`build_smb_os.py`) usa Groq (`llama-3.3-70b-versatile`) para todas as etapas: identificar a próxima tarefa, definir estrutura e gerar código. Não há revisão do código gerado.

O objetivo é separar responsabilidades: Gemini assume o raciocínio (planejamento e revisão) aproveitando seu contexto longo, enquanto Groq continua como gerador de código (rápido e econômico).

---

## Arquitetura

Três arquivos em `.github/scripts/`:

```
gemini_client.py   — planejar() + revisar()
groq_client.py     — gerar_codigo()
build_smb_os.py    — orquestrador
```

### `gemini_client.py`
- SDK: `google-generativeai`
- Modelo: `gemini-2.0-flash`
- Função `planejar(projeto_txt: str, codigo: str) -> dict`  
  Retorna: `{tarefa, descricao, arquivos, estrutura_sugerida}`
- Função `revisar(spec: dict, codigo_gerado: str) -> tuple[bool, str]`  
  Retorna: `(aprovado, feedback)`

### `groq_client.py`
- SDK: `groq`
- Modelo: `llama-3.3-70b-versatile`
- Função `gerar_codigo(spec: dict, projeto_txt: str, codigo_atual: str, feedback: str = "") -> str`  
  Retorna: string com blocos `=== ARQUIVO: ... === FIM ===`  
  Quando `feedback` está presente, o prompt inclui: `"REVISÃO ANTERIOR REPROVADA. Feedback: {feedback}\n\nCorriga os problemas e reimplemente."`

### `build_smb_os.py` (orquestrador)
Lê arquivos, chama os clients em sequência, gerencia o loop de revisão, salva arquivos gerados e escreve o log. ~80 linhas.

---

## Fluxo de dados

```
1. Lê PROJETO.txt + código existente
2. gemini_client.planejar()      → spec dict
3. groq_client.gerar_codigo()    → código bruto
4. gemini_client.revisar()       → (aprovado, feedback)
5. Se reprovado e tentativas < 3:
     groq_client.gerar_codigo(..., feedback=feedback)
     volta ao passo 4
6. Salva arquivos + log + commit
```

Máximo de **3 rodadas** de revisão. Após a terceira sem aprovação, commita o último código gerado com aviso no log.

---

## Tratamento de erros

| Situação | Comportamento |
|---|---|
| Gemini planejamento falha | Aborta — sem spec não há direção |
| Groq geração falha | Aborta — nada para revisar |
| Gemini revisão falha (API error) | Trata como aprovado — não bloqueia pipeline por instabilidade de API |
| 3 rodadas sem aprovação | Commita com aviso `⚠️ revisão não aprovada após 3 tentativas` no log |
| Nenhum arquivo gerado pelo Groq | Aborta antes do commit — evita commit vazio |

---

## Mudanças no workflow

**`build-deploy-smb-os.yml`** — dois ajustes no step "Instalar dependencias globais":
```yaml
pip install groq google-generativeai
```

E no step "Gerar codigo com Groq" (passa a se chamar "Gerar codigo"):
```yaml
env:
  GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

---

## O que não muda

- Workflow `orquestrador-agentes-diario.yml` — sem alteração
- Formato dos arquivos gerados (`=== ARQUIVO: ... === FIM ===`)
- Formato do log em `sugestoes/01-SMB-OS/`
- Lógica de commit/push

---

## Secret necessário

`GEMINI_API_KEY` já configurado nos secrets do repositório GitHub.
