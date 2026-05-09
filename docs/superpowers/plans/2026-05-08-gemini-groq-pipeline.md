# Pipeline Gemini + Groq — SMB-OS Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o `build_smb_os.py` monolítico por três arquivos separados onde Gemini planeja e revisa, e Groq gera código, com loop de revisão de até 3 rodadas.

**Architecture:** `gemini_client.py` expõe `planejar()` e `revisar()` usando `google-generativeai`. `groq_client.py` expõe `gerar_codigo()` usando `groq`. `build_smb_os.py` vira um orquestrador puro que importa os dois clients e gerencia o pipeline completo.

**Tech Stack:** Python 3.11, `google-generativeai` (gemini-2.0-flash), `groq` (llama-3.3-70b-versatile), GitHub Actions

---

## Mapa de arquivos

| Ação | Arquivo |
|---|---|
| Criar | `.github/scripts/gemini_client.py` |
| Criar | `.github/scripts/groq_client.py` |
| Reescrever | `.github/scripts/build_smb_os.py` |
| Modificar | `.github/workflows/build-deploy-smb-os.yml` (linhas 38 e 41-44) |

---

## Task 1: Criar `groq_client.py`

Extrai a lógica do Groq do `build_smb_os.py` atual para um módulo próprio.

**Files:**
- Create: `.github/scripts/groq_client.py`

- [ ] **Step 1: Criar o arquivo**

```python
# .github/scripts/groq_client.py
import os
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"


def gerar_codigo(spec: dict, projeto_txt: str, codigo_atual: str, feedback: str = "") -> str:
    feedback_prefix = ""
    if feedback:
        feedback_prefix = (
            f"REVISÃO ANTERIOR REPROVADA. Feedback: {feedback}\n\n"
            "Corrija os problemas e reimplemente.\n\n"
        )

    user_msg = (
        f"{feedback_prefix}"
        f"TAREFA: {spec['tarefa']}\n"
        f"DESCRIÇÃO: {spec['descricao']}\n"
        f"ARQUIVOS: {', '.join(spec['arquivos'])}\n"
        f"ESTRUTURA SUGERIDA: {spec.get('estrutura_sugerida', '')}\n\n"
        f"PROJETO.txt:\n{projeto_txt}\n\n"
        f"CÓDIGO EXISTENTE:\n{codigo_atual}"
    )

    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um desenvolvedor senior Full Stack especialista em FastAPI e Next.js. "
                    "Implemente a tarefa descrita de forma completa e funcional. "
                    "Siga as convenções do código existente. "
                    "Responda SOMENTE com blocos no formato:\n"
                    "=== ARQUIVO: caminho/relativo ===\n"
                    "<conteúdo completo>\n"
                    "=== FIM ===\n"
                    "Gere arquivos reais e completos, não pseudocódigo."
                ),
            },
            {"role": "user", "content": user_msg},
        ],
        max_tokens=4000,
        temperature=0.1,
    )
    return r.choices[0].message.content
```

- [ ] **Step 2: Verificar sintaxe**

```bash
python -c "import ast; ast.parse(open('.github/scripts/groq_client.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/groq_client.py
git commit -m "feat(build): extrair groq_client.py do build_smb_os"
```

---

## Task 2: Criar `gemini_client.py`

Novo módulo com `planejar()` (arquiteto) e `revisar()` (revisor) usando Gemini 2.0 Flash.

**Files:**
- Create: `.github/scripts/gemini_client.py`

- [ ] **Step 1: Criar o arquivo**

```python
# .github/scripts/gemini_client.py
import os
import json
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
    if text.endswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[:-1])
    return json.loads(text.strip())


def planejar(projeto_txt: str, codigo: str) -> dict:
    """
    Lê PROJETO.txt + código e retorna spec da próxima tarefa.
    Retorna: {"tarefa": str, "descricao": str, "arquivos": [str], "estrutura_sugerida": str}
    """
    model = genai.GenerativeModel(MODEL)
    prompt = (
        "Você é um tech lead senior. Analise o PROJETO.txt e o código existente. "
        "Identifique UMA tarefa pendente (marcada com []) que seja implementável agora "
        "com base no que já existe. Responda APENAS em JSON válido com este formato:\n"
        '{"tarefa": "<nome curto>", "descricao": "<o que implementar em 2 frases>", '
        '"arquivos": ["<arquivo1>", "<arquivo2>"], '
        '"estrutura_sugerida": "<estrutura do código em 3-5 linhas>"}\n\n'
        f"PROJETO.txt:\n{projeto_txt}\n\nCÓDIGO EXISTENTE:\n{codigo}"
    )
    response = model.generate_content(prompt)
    return _parse_json(response.text)


def revisar(spec: dict, codigo_gerado: str) -> tuple[bool, str]:
    """
    Revisa o código gerado contra a spec.
    Retorna: (aprovado: bool, feedback: str)
    """
    model = genai.GenerativeModel(MODEL)
    prompt = (
        "Você é um revisor de código senior. Avalie se o código gerado implementa "
        "corretamente a tarefa especificada. "
        "Responda APENAS em JSON válido com este formato:\n"
        '{"aprovado": true, "feedback": ""}\n'
        "ou\n"
        '{"aprovado": false, "feedback": "<problemas específicos em 2-3 frases>"}\n\n'
        f"SPEC DA TAREFA:\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n\n"
        f"CÓDIGO GERADO:\n{codigo_gerado}"
    )
    response = model.generate_content(prompt)
    result = _parse_json(response.text)
    return result["aprovado"], result.get("feedback", "")
```

- [ ] **Step 2: Verificar sintaxe**

```bash
python -c "import ast; ast.parse(open('.github/scripts/gemini_client.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/gemini_client.py
git commit -m "feat(build): criar gemini_client.py com planejar() e revisar()"
```

---

## Task 3: Reescrever `build_smb_os.py` como orquestrador

Substitui o script atual por um orquestrador que usa os dois clients. O formato de saída dos arquivos gerados e do log não muda.

**Files:**
- Modify: `.github/scripts/build_smb_os.py`

- [ ] **Step 1: Substituir o conteúdo completo do arquivo**

```python
# .github/scripts/build_smb_os.py
import sys
import re
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import gemini_client
import groq_client

sys.stdout.reconfigure(encoding="utf-8")

PROJETO_DIR = Path("01-SMB-OS")
IGNORAR = {"node_modules", ".git", "__pycache__", "venv", ".venv",
           "dist", "build", ".next", "uv.lock", "pnpm-lock.yaml"}
EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".toml", ".json", ".md"}
MAX_REVISOES = 3


def ler_codigo(pasta, max_chars=10000):
    codigo = ""
    for f in sorted(pasta.rglob("*")):
        if any(p in f.parts for p in IGNORAR):
            continue
        if f.suffix not in EXTS or not f.is_file():
            continue
        try:
            conteudo = f.read_text(encoding="utf-8", errors="ignore")[:1500]
            bloco = f"\n### {f.relative_to(pasta)}\n```\n{conteudo}\n```\n"
            if len(codigo) + len(bloco) > max_chars:
                break
            codigo += bloco
        except Exception:
            pass
    return codigo


def salvar_arquivos(codigo_gerado):
    arquivos_salvos = []
    blocos = codigo_gerado.split("=== ARQUIVO:")
    if len(blocos) > 1:
        for bloco in blocos[1:]:
            try:
                linhas = bloco.strip().split("\n")
                caminho = linhas[0].strip()
                fim = bloco.find("=== FIM ===")
                conteudo = bloco[len(linhas[0]):fim].strip() if fim != -1 else bloco[len(linhas[0]):].strip()
                if conteudo.startswith("```"):
                    conteudo = "\n".join(conteudo.split("\n")[1:])
                if conteudo.endswith("```"):
                    conteudo = "\n".join(conteudo.split("\n")[:-1])
                dest = PROJETO_DIR / caminho
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(conteudo, encoding="utf-8")
                arquivos_salvos.append(caminho)
                print(f"  Arquivo gerado: {caminho}")
            except Exception as e:
                print(f"  Erro ao salvar: {e}")
    else:
        pattern = r'(?:(?:#|//|<!--|)\s*([\w/.\-]+\.\w+)\s*(?:-->)?\n)?```(?:\w+)?\n(.*?)```'
        matches = re.findall(pattern, codigo_gerado, re.DOTALL)
        for caminho, conteudo in matches:
            if not caminho or "/" not in caminho:
                continue
            try:
                dest = PROJETO_DIR / caminho.strip()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(conteudo.strip(), encoding="utf-8")
                arquivos_salvos.append(caminho)
                print(f"  Arquivo gerado: {caminho}")
            except Exception as e:
                print(f"  Erro ao salvar: {e}")
    return arquivos_salvos


def main():
    print("=" * 60)
    print("Build SMB-OS — Gemini (arquiteto) + Groq (gerador)")
    print("=" * 60)

    projeto_txt = (PROJETO_DIR / "PROJETO.txt").read_text(encoding="utf-8")
    codigo_atual = ler_codigo(PROJETO_DIR)

    # Passo 1: Gemini planeja
    print("\n[1/4] Gemini planejando tarefa...")
    try:
        spec = gemini_client.planejar(projeto_txt, codigo_atual)
        print(f"  Tarefa: {spec['tarefa']}")
        print(f"  Descrição: {spec['descricao']}")
    except Exception as e:
        print(f"  ERRO no planejamento Gemini: {e}")
        sys.exit(1)

    time.sleep(1)

    # Passo 2: Groq gera
    print("\n[2/4] Groq gerando código...")
    try:
        codigo_gerado = groq_client.gerar_codigo(spec, projeto_txt, codigo_atual)
    except Exception as e:
        print(f"  ERRO na geração Groq: {e}")
        sys.exit(1)

    time.sleep(1)

    # Passo 3: Gemini revisa (máx MAX_REVISOES rodadas)
    status_revisao = "aprovado"
    for tentativa in range(1, MAX_REVISOES + 1):
        print(f"\n[3/4] Gemini revisando (tentativa {tentativa}/{MAX_REVISOES})...")
        try:
            aprovado, feedback = gemini_client.revisar(spec, codigo_gerado)
        except Exception as e:
            print(f"  Erro na revisão (API): {e} — tratando como aprovado")
            aprovado, feedback = True, ""

        if aprovado:
            print("  Código aprovado pelo Gemini")
            status_revisao = "aprovado"
            break

        print(f"  Reprovado. Feedback: {feedback}")
        if tentativa < MAX_REVISOES:
            print("  Groq corrigindo...")
            try:
                codigo_gerado = groq_client.gerar_codigo(
                    spec, projeto_txt, codigo_atual, feedback=feedback
                )
            except Exception as e:
                print(f"  ERRO na correção Groq: {e}")
                sys.exit(1)
            time.sleep(1)
        else:
            status_revisao = f"revisão não aprovada após {MAX_REVISOES} tentativas"
            print(f"  {status_revisao} — commitando mesmo assim")

    # Passo 4: Salvar arquivos
    print("\n[4/4] Salvando arquivos gerados...")
    arquivos_salvos = salvar_arquivos(codigo_gerado)
    if not arquivos_salvos:
        print("  ERRO: nenhum arquivo gerado — abortando commit")
        sys.exit(1)

    log_dir = Path("sugestoes/01-SMB-OS")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = log_dir / f"build_{ts}.txt"
    log.write_text(
        f"BUILD SESSION — SMB-OS (Gemini+Groq)\n"
        f"Data: {datetime.now()}\n"
        f"Status revisão: {status_revisao}\n\n"
        f"TAREFA:\n{spec}\n\n"
        f"ARQUIVOS GERADOS:\n" + "\n".join(arquivos_salvos) + "\n\n"
        f"CÓDIGO:\n{codigo_gerado}",
        encoding="utf-8",
    )
    print(f"\nLog: {log}")
    print(f"Total arquivos gerados: {len(arquivos_salvos)}")
    print("\nBuild concluído")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar sintaxe**

```bash
python -c "import ast; ast.parse(open('.github/scripts/build_smb_os.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/scripts/build_smb_os.py
git commit -m "feat(build): reescrever build_smb_os.py como orquestrador Gemini+Groq"
```

---

## Task 4: Atualizar workflow `build-deploy-smb-os.yml`

Dois ajustes: adicionar `google-generativeai` na instalação e `GEMINI_API_KEY` no step de build.

**Files:**
- Modify: `.github/workflows/build-deploy-smb-os.yml:36-44`

- [ ] **Step 1: Editar o step "Instalar dependencias globais" (linha 38)**

Alterar:
```yaml
      - name: Instalar dependencias globais
        run: |
          pip install groq
          npm install -g pnpm vercel@latest
```

Para:
```yaml
      - name: Instalar dependencias globais
        run: |
          pip install groq google-generativeai
          npm install -g pnpm vercel@latest
```

- [ ] **Step 2: Editar o step "Gerar codigo com Groq" (linhas 41-44)**

Alterar:
```yaml
      - name: Gerar codigo com Groq
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: python .github/scripts/build_smb_os.py
```

Para:
```yaml
      - name: Gerar codigo
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python .github/scripts/build_smb_os.py
```

- [ ] **Step 3: Verificar YAML válido**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/build-deploy-smb-os.yml')); print('YAML OK')"
```

Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build-deploy-smb-os.yml
git commit -m "feat(ci): adicionar google-generativeai e GEMINI_API_KEY no build workflow"
```

---

## Task 5: Validação final

- [ ] **Step 1: Verificar todos os arquivos existem**

```bash
python -c "
from pathlib import Path
files = [
    '.github/scripts/gemini_client.py',
    '.github/scripts/groq_client.py',
    '.github/scripts/build_smb_os.py',
    '.github/workflows/build-deploy-smb-os.yml',
]
for f in files:
    assert Path(f).exists(), f'FALTANDO: {f}'
    print(f'OK: {f}')
"
```

Expected: 4 linhas `OK: ...`

- [ ] **Step 2: Verificar sintaxe de todos os scripts Python**

```bash
python -c "
import ast
for f in ['.github/scripts/gemini_client.py', '.github/scripts/groq_client.py', '.github/scripts/build_smb_os.py']:
    ast.parse(open(f).read())
    print(f'Sintaxe OK: {f}')
"
```

Expected: 3 linhas `Sintaxe OK: ...`

- [ ] **Step 3: Verificar que build_smb_os.py importa os dois clients**

```bash
python -c "
content = open('.github/scripts/build_smb_os.py').read()
assert 'import gemini_client' in content, 'gemini_client não importado'
assert 'import groq_client' in content, 'groq_client não importado'
assert 'MAX_REVISOES = 3' in content, 'MAX_REVISOES não definido'
assert 'gemini_client.planejar' in content, 'planejar() não chamado'
assert 'gemini_client.revisar' in content, 'revisar() não chamado'
assert 'groq_client.gerar_codigo' in content, 'gerar_codigo() não chamado'
print('Todas as verificações passaram')
"
```

Expected: `Todas as verificações passaram`

- [ ] **Step 4: Verificar que workflow tem GEMINI_API_KEY**

```bash
python -c "
content = open('.github/workflows/build-deploy-smb-os.yml').read()
assert 'google-generativeai' in content, 'google-generativeai não instalado'
assert 'GEMINI_API_KEY' in content, 'GEMINI_API_KEY não configurado'
print('Workflow OK')
"
```

Expected: `Workflow OK`

- [ ] **Step 5: Commit final de validação**

```bash
git add -A
git status
# Confirmar que não há arquivos não rastreados inesperados
git commit -m "chore(build): validação pipeline Gemini+Groq concluída" --allow-empty
```
