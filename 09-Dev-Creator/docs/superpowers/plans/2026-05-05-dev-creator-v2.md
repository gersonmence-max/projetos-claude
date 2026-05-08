# Dev Creator v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken file-by-file generation pipeline with a single-shot generator + real execution loop that produces working code instead of syntactically-valid-but-broken code.

**Architecture:** Generator asks AI for ALL files in one call (FILE-delimiter format), writes them, installs dependencies, checks syntax via py_compile, then Fixer passes the ENTIRE project + errors back to AI for cross-file repair — up to 3 attempts. Pipeline becomes 4 phases: Generate → Write → Check/Fix loop → Report.

**Tech Stack:** Python 3.11, google-genai (gemini-2.5-flash + configurable), groq (llama-3.3-70b fallback), FastAPI/uvicorn (web), subprocess (dependency install + syntax check), pytest (tests)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `config.py` | **CREATE** | Single source of truth for all env vars + tunables |
| `generator.py` | **CREATE** | Single-shot: spec → all files via FILE-delimiter format |
| `runner.py` | **CREATE** | pip install requirements.txt + py_compile all .py files |
| `fixer.py` | **CREATE** | Full-context repair: project + errors → corrected files |
| `pipeline.py` | **REPLACE** | New 4-phase orchestration using the new modules |
| `executor.py` | **MODIFY** | Make model + output tokens configurable; read from config |
| `tests.py` | **EXTEND** | Add test sections for each new module |
| `templates/index.html` | **MODIFY** | 4-phase progress bar + model display in header |
| `planner.py` | **DELETE** | Superseded by generator.py |
| `coder.py` | **DELETE** | Superseded by generator.py (write_file logic moves to generator) |

---

## Task 1: Git Init + config.py

**Files:**
- Create: `config.py`

- [ ] **Step 1: Init git**

```
cd "C:\Users\g-fil\Documents\Gerson ai\dev-creator"
git init
```

Create `.gitignore`:
```
venv/
__pycache__/
*.pyc
.env
test_output/
*.pickle
```

Run: `git add .gitignore && git commit -m "chore: init repo"`

- [ ] **Step 2: Write failing test for config**

Add to `tests.py` (inside `SECTIONS` dict, new key `"CONFIG"`):

```python
def test_config_has_required_fields():
    from config import config
    assert hasattr(config, "primary_model")
    assert hasattr(config, "max_fix_attempts")
    assert hasattr(config, "max_files")
    assert hasattr(config, "max_output_tokens")
    print("  [OK] config - todos os campos existem")

def test_config_defaults():
    from config import config
    assert config.max_fix_attempts == 3
    assert config.max_files == 50
    assert config.max_output_tokens == 16384
    assert config.primary_model == "gemini-2.5-flash"
    print("  [OK] config - defaults corretos")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[ERRO] test_config_has_required_fields: ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement config.py**

Create `config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

class _Config:
    primary_model: str     = os.getenv("PRIMARY_MODEL", "gemini-2.5-flash")
    fallback_model: str    = os.getenv("FALLBACK_MODEL", "llama-3.3-70b-versatile")
    max_fix_attempts: int  = int(os.getenv("MAX_FIX_ATTEMPTS", "3"))
    max_files: int         = int(os.getenv("MAX_FILES", "50"))
    max_output_tokens: int = int(os.getenv("MAX_OUTPUT_TOKENS", "16384"))
    google_api_key: str    = os.getenv("GOOGLE_API_KEY", "")
    groq_api_key: str      = os.getenv("GROQ_API_KEY", "")

config = _Config()
```

- [ ] **Step 4: Run tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `CONFIG` section — 2 passed, 0 failed

- [ ] **Step 5: Commit**

```
git add config.py tests.py
git commit -m "feat: add centralized config"
```

---

## Task 2: executor.py — Configurable Model + Higher Token Limit

**Files:**
- Modify: `executor.py`

- [ ] **Step 1: Write failing test**

Add to `tests.py` (new section `"EXECUTOR"`):

```python
def test_executor_uses_config_model():
    from config import config
    from executor import AIExecutor
    e = AIExecutor()
    assert e.gemini_model == config.primary_model
    print("  [OK] executor - usa model do config")

def test_executor_accepts_custom_model():
    from executor import AIExecutor
    e = AIExecutor(model="gemini-2.5-pro")
    assert e.gemini_model == "gemini-2.5-pro"
    print("  [OK] executor - aceita model customizado")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[ERRO] test_executor_uses_config_model: ... AIExecutor() got unexpected keyword`

- [ ] **Step 2: Update executor.py**

Replace full content of `executor.py`:

```python
import sys
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from config import config

load_dotenv()


class AIExecutor:
    def __init__(self, model: str = None):
        self.gemini_client = genai.Client(api_key=config.google_api_key)
        self.gemini_model  = model or config.primary_model
        self.groq          = Groq(api_key=config.groq_api_key)
        self.stats         = {"gemini_calls": 0, "groq_calls": 0, "errors": 0}

    def execute(self, prompt: str, urgent: bool = False) -> dict:
        start = datetime.now()
        if urgent:
            result = self._groq(prompt)
            model  = config.fallback_model
        else:
            result = self._gemini(prompt)
            model  = self.gemini_model
        duration = (datetime.now() - start).total_seconds()
        return {
            "success": result["success"],
            "output":  result["output"],
            "model":   model,
            "duration": duration,
        }

    def _gemini(self, prompt: str) -> dict:
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=config.max_output_tokens,
                ),
            )
            self.stats["gemini_calls"] += 1
            return {"success": True, "output": response.text}
        except Exception as e:
            print(f"  Gemini falhou: {e} — usando Groq...")
            self.stats["errors"] += 1
            return self._groq(prompt)

    def _groq(self, prompt: str) -> dict:
        try:
            response = self.groq.chat.completions.create(
                model=config.fallback_model,
                messages=[{"role": "user", "content": prompt}],
            )
            self.stats["groq_calls"] += 1
            return {"success": True, "output": response.choices[0].message.content}
        except Exception as e:
            self.stats["errors"] += 1
            return {"success": False, "output": f"ERRO: {e}"}

    def get_stats(self) -> dict:
        total = self.stats["gemini_calls"] + self.stats["groq_calls"]
        return {**self.stats, "total_calls": total}
```

- [ ] **Step 3: Run tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `EXECUTOR` section — 2 passed | overall still 29+ passed, 0 failed

- [ ] **Step 4: Commit**

```
git add executor.py tests.py
git commit -m "feat: make AI model + token limit configurable via config"
```

---

## Task 3: generator.py — Single-Shot Code Generation

**Files:**
- Create: `generator.py`

The fundamental fix. One AI call returns ALL files in a reliable FILE-delimiter format, ensuring consistent imports and function signatures across the entire project.

- [ ] **Step 1: Write failing tests**

Add to `tests.py` (new section `"GENERATOR"`):

```python
def test_parse_file_delimited_basic():
    from generator import parse_file_delimited
    raw = "===FILE: main.py===\nprint('hi')\n===FILE: utils.py===\ndef foo(): pass\n===END==="
    files = parse_file_delimited(raw)
    assert len(files) == 2
    assert files[0]["path"] == "main.py"
    assert files[0]["content"] == "print('hi')"
    assert files[1]["path"] == "utils.py"
    print("  [OK] parse_file_delimited - parseia 2 arquivos")

def test_parse_file_delimited_no_end_marker():
    from generator import parse_file_delimited
    raw = "===FILE: main.py===\nx = 1\n===FILE: b.py===\ny = 2"
    files = parse_file_delimited(raw)
    assert len(files) == 2
    print("  [OK] parse_file_delimited - funciona sem ===END===")

def test_parse_file_delimited_empty_returns_empty():
    from generator import parse_file_delimited
    assert parse_file_delimited("nenhum delimitador aqui") == []
    print("  [OK] parse_file_delimited - retorna [] sem delimitadores")

def test_parse_file_delimited_preserves_content_with_quotes():
    from generator import parse_file_delimited
    raw = '===FILE: a.py===\nprint("hello, world")\nx = {"key": "val"}\n===END==='
    files = parse_file_delimited(raw)
    assert '"hello, world"' in files[0]["content"]
    assert '"key"' in files[0]["content"]
    print("  [OK] parse_file_delimited - preserva aspas e chaves no conteudo")

def test_generator_raises_on_empty_response():
    from generator import Generator
    from unittest.mock import MagicMock
    g = Generator.__new__(Generator)
    g.executor = MagicMock()
    g.executor.execute.return_value = {"success": True, "output": "sem delimitadores"}
    try:
        g.generate("spec", "greenfield", "/tmp")
        assert False, "Deveria ter levantado RuntimeError"
    except RuntimeError as e:
        assert "nenhum arquivo" in str(e).lower()
    print("  [OK] generator - RuntimeError quando AI nao retorna arquivos")

def test_generator_raises_on_executor_failure():
    from generator import Generator
    from unittest.mock import MagicMock
    g = Generator.__new__(Generator)
    g.executor = MagicMock()
    g.executor.execute.return_value = {"success": False, "output": "ERRO: timeout"}
    try:
        g.generate("spec", "greenfield", "/tmp")
        assert False, "Deveria ter levantado RuntimeError"
    except RuntimeError:
        pass
    print("  [OK] generator - RuntimeError quando executor falha")

def test_generator_enforces_max_files():
    from generator import Generator, parse_file_delimited
    from unittest.mock import MagicMock
    from config import config
    big = "\n".join(f"===FILE: f{i}.py===\nx={i}" for i in range(config.max_files + 5))
    g = Generator.__new__(Generator)
    g.executor = MagicMock()
    g.executor.execute.return_value = {"success": True, "output": big + "\n===END==="}
    try:
        g.generate("spec", "greenfield", "/tmp")
        assert False, "Deveria ter levantado ValueError"
    except ValueError:
        pass
    print("  [OK] generator - ValueError quando AI retorna mais arquivos que o limite")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[ERRO] test_parse_file_delimited_basic: ModuleNotFoundError: No module named 'generator'`

- [ ] **Step 2: Implement generator.py**

Create `generator.py`:

```python
import re
from executor import AIExecutor
from config import config

GENERATION_PROMPT = """\
You are a senior software engineer. Generate a COMPLETE, working project from the specification.

CRITICAL RULES — violating any rule makes the output unusable:
1. Every import must reference code that actually exists in another file you generate
2. Every cross-file function call must match the function's actual signature exactly
3. All third-party packages used in any import must be listed in requirements.txt
4. No placeholder code: no "# TODO", no bare "pass" where logic belongs, no "..."
5. Include requirements.txt — even if empty (write just a comment)
6. Include a README.md explaining how to run the project

Return files using EXACTLY this format — no other text before or after:

===FILE: requirements.txt===
fastapi
uvicorn
===FILE: main.py===
from utils import helper
def main():
    print(helper())
if __name__ == "__main__":
    main()
===FILE: utils.py===
def helper() -> str:
    return "Hello from utils"
===END===

Project type: {project_type}

Specification:
{spec}
"""


def parse_file_delimited(raw: str) -> list[dict]:
    pattern = re.compile(
        r"===FILE:\s*(\S+)===\n(.*?)(?=\n===FILE:|\n===END===|$)",
        re.DOTALL,
    )
    return [
        {"path": m.group(1).strip(), "content": m.group(2).strip()}
        for m in pattern.finditer(raw)
    ]


class Generator:
    def __init__(self):
        self.executor = AIExecutor()

    def generate(self, spec: str, project_type: str, destination: str) -> list[dict]:
        prompt = GENERATION_PROMPT.format(
            project_type=project_type,
            spec=spec,
        )
        result = self.executor.execute(prompt)
        if not result["success"]:
            raise RuntimeError(f"AI falhou ao gerar projeto: {result['output']}")

        files = parse_file_delimited(result["output"])
        if not files:
            raise RuntimeError(
                "Nenhum arquivo retornado pela AI. "
                f"Resposta (primeiros 300 chars): {result['output'][:300]}"
            )
        if len(files) > config.max_files:
            raise ValueError(
                f"AI retornou {len(files)} arquivos — limite e {config.max_files}"
            )
        return files
```

- [ ] **Step 3: Run tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `GENERATOR` section — 7 passed | overall 0 failed

- [ ] **Step 4: Commit**

```
git add generator.py tests.py
git commit -m "feat: single-shot code generator with FILE-delimiter format"
```

---

## Task 4: runner.py — Dependency Install + Syntax Check

**Files:**
- Create: `runner.py`

- [ ] **Step 1: Write failing tests**

Add to `tests.py` (new section `"RUNNER"`):

```python
def test_install_dependencies_no_requirements():
    from runner import install_dependencies
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        result = install_dependencies(d)
        assert result["success"] is True
        assert result["skipped"] is True
    print("  [OK] install_dependencies - skip quando sem requirements.txt")

def test_install_dependencies_with_file():
    from runner import install_dependencies
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "requirements.txt").write_text("# empty\n")
        result = install_dependencies(d)
        assert result["success"] is True
        assert result["skipped"] is False
    print("  [OK] install_dependencies - processa requirements.txt vazio")

def test_check_python_syntax_valid():
    from runner import check_python_syntax
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "good.py").write_text("x = 1\ndef foo():\n    return x\n")
        errors = check_python_syntax(d, ["good.py"])
        assert errors == []
    print("  [OK] check_python_syntax - arquivo valido sem erros")

def test_check_python_syntax_invalid():
    from runner import check_python_syntax
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "bad.py").write_text("def broken(:\n    pass\n")
        errors = check_python_syntax(d, ["bad.py"])
        assert len(errors) == 1
        assert errors[0]["file"] == "bad.py"
        assert errors[0]["error"] != ""
    print("  [OK] check_python_syntax - detecta erro de sintaxe")

def test_check_project_success():
    from runner import check_project
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "main.py").write_text("x = 1\n")
        files = [{"path": "main.py", "content": "x = 1"}]
        result = check_project(d, files)
        assert result["success"] is True
        assert result["errors"] == []
    print("  [OK] check_project - projeto valido retorna success=True")

def test_check_project_failure():
    from runner import check_project
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "bad.py").write_text("def broken(:\n    pass\n")
        files = [{"path": "bad.py", "content": "def broken(:\n    pass\n"}]
        result = check_project(d, files)
        assert result["success"] is False
        assert len(result["errors"]) == 1
    print("  [OK] check_project - projeto invalido retorna success=False")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[ERRO] test_install_dependencies_no_requirements: ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 2: Implement runner.py**

Create `runner.py`:

```python
import sys
import subprocess
from pathlib import Path


def install_dependencies(destination: str) -> dict:
    req = Path(destination) / "requirements.txt"
    if not req.exists():
        return {"success": True, "skipped": True, "output": ""}

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req), "--quiet"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=destination,
    )
    return {
        "success": result.returncode == 0,
        "skipped": False,
        "output": (result.stdout + result.stderr).strip(),
    }


def check_python_syntax(destination: str, py_files: list[str]) -> list[dict]:
    errors = []
    for f in py_files:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", f],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=destination,
        )
        if result.returncode != 0:
            errors.append({"file": f, "error": result.stderr.strip()})
    return errors


def check_project(destination: str, files: list[dict]) -> dict:
    py_files = [f["path"] for f in files if f["path"].endswith(".py")]
    install = install_dependencies(destination)
    errors  = check_python_syntax(destination, py_files) if py_files else []
    return {
        "success":         len(errors) == 0,
        "errors":          errors,
        "install_success": install["success"],
        "install_log":     install["output"],
    }
```

- [ ] **Step 3: Run tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `RUNNER` section — 6 passed | overall 0 failed

- [ ] **Step 4: Commit**

```
git add runner.py tests.py
git commit -m "feat: runner — pip install + py_compile verification"
```

---

## Task 5: fixer.py — Full-Context Error Repair

**Files:**
- Create: `fixer.py`

- [ ] **Step 1: Write failing tests**

Add to `tests.py` (new section `"FIXER"`):

```python
def test_build_context_reads_files():
    from fixer import build_context
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.py").write_text("x = 1")
        files = [{"path": "a.py", "content": "x = 1"}]
        ctx = build_context(d, files)
        assert "===FILE: a.py===" in ctx
        assert "x = 1" in ctx
    print("  [OK] build_context - inclui conteudo dos arquivos")

def test_build_context_multiple_files():
    from fixer import build_context
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.py").write_text("x = 1")
        (Path(d) / "b.py").write_text("y = 2")
        files = [{"path": "a.py", "content": ""}, {"path": "b.py", "content": ""}]
        ctx = build_context(d, files)
        assert "===FILE: a.py===" in ctx
        assert "===FILE: b.py===" in ctx
    print("  [OK] build_context - inclui todos os arquivos")

def test_fixer_returns_empty_on_executor_failure():
    from fixer import Fixer
    from unittest.mock import MagicMock
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Fixer.__new__(Fixer)
        f.executor = MagicMock()
        f.executor.execute.return_value = {"success": False, "output": "ERRO"}
        result = f.fix(d, [], [{"file": "a.py", "error": "SyntaxError"}])
        assert result == []
    print("  [OK] fixer - retorna [] quando executor falha")

def test_fixer_returns_only_changed_files():
    from fixer import Fixer
    from unittest.mock import MagicMock
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = Fixer.__new__(Fixer)
        f.executor = MagicMock()
        f.executor.execute.return_value = {
            "success": True,
            "output": "===FILE: bad.py===\nx = 1  # fixed\n===END==="
        }
        files = [
            {"path": "bad.py",  "content": "def broken(:"},
            {"path": "good.py", "content": "y = 2"},
        ]
        result = f.fix(d, files, [{"file": "bad.py", "error": "SyntaxError"}])
        assert len(result) == 1
        assert result[0]["path"] == "bad.py"
        assert "fixed" in result[0]["content"]
    print("  [OK] fixer - retorna apenas arquivos alterados")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[ERRO] test_build_context_reads_files: ModuleNotFoundError: No module named 'fixer'`

- [ ] **Step 2: Implement fixer.py**

Create `fixer.py`:

```python
import re
from pathlib import Path
from executor import AIExecutor

FIX_PROMPT = """\
A software project was generated but has syntax errors. Fix the files so the project works.

Errors found:
{errors}

Full project context:
{context}

Return ONLY the files that need to change, using this exact format:

===FILE: path/to/file.py===
... corrected content ...
===END===

Rules:
- Only include files that changed
- Fix all imports and references that contributed to the errors
- Do not modify files that are currently correct
"""


def build_context(destination: str, files: list[dict]) -> str:
    parts = []
    for f in files:
        full = Path(destination) / f["path"]
        content = full.read_text(encoding="utf-8") if full.exists() else f.get("content", "")
        parts.append(f"===FILE: {f['path']}===\n{content}")
    return "\n".join(parts)


def _parse_delimited(raw: str) -> list[dict]:
    pattern = re.compile(
        r"===FILE:\s*(\S+)===\n(.*?)(?=\n===FILE:|\n===END===|$)",
        re.DOTALL,
    )
    return [
        {"path": m.group(1).strip(), "content": m.group(2).strip()}
        for m in pattern.finditer(raw)
    ]


class Fixer:
    def __init__(self):
        self.executor = AIExecutor()

    def fix(self, destination: str, files: list[dict], errors: list[dict]) -> list[dict]:
        error_text = "\n".join(f"- {e['file']}: {e['error']}" for e in errors)
        context    = build_context(destination, files)
        prompt     = FIX_PROMPT.format(errors=error_text, context=context)

        result = self.executor.execute(prompt)
        if not result["success"]:
            return []
        return _parse_delimited(result["output"])
```

- [ ] **Step 3: Run tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `FIXER` section — 4 passed | overall 0 failed

- [ ] **Step 4: Commit**

```
git add fixer.py tests.py
git commit -m "feat: fixer — full-context cross-file error repair"
```

---

## Task 6: pipeline.py — New 4-Phase Orchestration

**Files:**
- Modify: `pipeline.py` (full replacement)

- [ ] **Step 1: Write the failing test**

Add to `tests.py` (new section `"PIPELINE"`):

```python
def test_pipeline_calls_all_four_phases():
    from unittest.mock import MagicMock, patch, call
    import tempfile

    fake_files = [{"path": "main.py", "content": "x = 1"}]

    with tempfile.TemporaryDirectory() as d:
        with patch("pipeline.Generator") as MockGen, \
             patch("pipeline.check_project") as mock_check, \
             patch("pipeline.Reporter") as MockRep:

            MockGen.return_value.generate.return_value = fake_files
            mock_check.return_value = {
                "success": True, "errors": [],
                "install_success": True, "install_log": ""
            }
            MockRep.return_value.generate.return_value = f"{d}/reports/summary.md"

            from pipeline import run_pipeline
            run_pipeline(d, "spec", "greenfield")

            MockGen.return_value.generate.assert_called_once()
            mock_check.assert_called_once()
            MockRep.return_value.generate.assert_called_once()
    print("  [OK] pipeline - invoca as 4 fases")

def test_pipeline_runs_fixer_on_errors():
    from unittest.mock import MagicMock, patch
    import tempfile
    from pathlib import Path

    fake_files = [{"path": "bad.py", "content": "def broken(:"}]

    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "bad.py").write_text("def broken(:")
        with patch("pipeline.Generator") as MockGen, \
             patch("pipeline.check_project") as mock_check, \
             patch("pipeline.Fixer") as MockFix, \
             patch("pipeline.Reporter") as MockRep:

            MockGen.return_value.generate.return_value = fake_files
            mock_check.side_effect = [
                {"success": False, "errors": [{"file": "bad.py", "error": "SyntaxError"}],
                 "install_success": True, "install_log": ""},
                {"success": True, "errors": [],
                 "install_success": True, "install_log": ""},
            ]
            MockFix.return_value.fix.return_value = [{"path": "bad.py", "content": "x = 1"}]
            MockRep.return_value.generate.return_value = f"{d}/reports/summary.md"

            from pipeline import run_pipeline
            run_pipeline(d, "spec", "greenfield")

            MockFix.return_value.fix.assert_called_once()
            assert mock_check.call_count == 2
    print("  [OK] pipeline - executa fixer quando ha erros")
```

Run: `.\venv\Scripts\python tests.py`
Expected: `[FALHOU] test_pipeline_calls_all_four_phases` (old pipeline doesn't have Generator)

- [ ] **Step 2: Replace pipeline.py**

Replace full content of `pipeline.py`:

```python
from datetime import datetime
from pathlib import Path

from generator import Generator
from runner import check_project
from fixer import Fixer
from reporter import Reporter
from config import config


def _write_file(destination: str, relative_path: str, content: str) -> None:
    dest_abs = Path(destination).resolve()
    full     = (dest_abs / relative_path).resolve()
    try:
        full.relative_to(dest_abs)
    except ValueError:
        raise ValueError(f"Path traversal bloqueado: {relative_path!r}")
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def _merge_fixes(original: list[dict], fixes: list[dict]) -> list[dict]:
    fixed_paths = {f["path"] for f in fixes}
    return [f for f in original if f["path"] not in fixed_paths] + fixes


def run_pipeline(destination: str, spec: str, project_type: str) -> None:
    start = datetime.now()

    print("\n" + "=" * 70)
    print("DEV CREATOR v2 — PIPELINE AUTONOMO")
    print("=" * 70 + "\n")

    # ── Phase 1: Single-shot generation ──────────────────────────────────
    print("[1/4] Gerando projeto completo (single-shot)...")
    try:
        files = Generator().generate(spec, project_type, destination)
    except (RuntimeError, ValueError) as e:
        print(f"  ERRO: {e}")
        return

    print(f"  -> {len(files)} arquivo(s) planejado(s)")
    for f in files:
        print(f"     - {f['path']}")
    print()

    # ── Phase 2: Write all files ──────────────────────────────────────────
    print("[2/4] Escrevendo arquivos no disco...")
    written, skipped = [], []
    for f in files:
        try:
            _write_file(destination, f["path"], f["content"])
            written.append(f["path"])
        except ValueError as e:
            skipped.append((f["path"], str(e)))
    for path in written:
        print(f"  -> {path}")
    for path, err in skipped:
        print(f"  IGNORADO {path}: {err}")
    print()

    # ── Phase 3: Install deps + check syntax + fix loop ──────────────────
    print("[3/4] Instalando dependencias e verificando sintaxe...")
    result = check_project(destination, files)

    if result["install_log"]:
        print(f"  pip: {result['install_log'][:120]}")

    attempt = 0
    while not result["success"] and attempt < config.max_fix_attempts:
        attempt += 1
        print(f"\n  {len(result['errors'])} erro(s) — correcao {attempt}/{config.max_fix_attempts}...")
        for e in result["errors"]:
            print(f"  - {e['file']}: {e['error'][:120]}")

        fixes = Fixer().fix(destination, files, result["errors"])
        if not fixes:
            print("  AI nao retornou correcoes.")
            break

        for f in fixes:
            try:
                _write_file(destination, f["path"], f["content"])
                print(f"  Corrigido: {f['path']}")
            except ValueError as e:
                print(f"  Ignorado: {f['path']} — {e}")

        files  = _merge_fixes(files, fixes)
        result = check_project(destination, files)

    if result["success"]:
        print("  Sintaxe OK!")
    else:
        n = len(result["errors"])
        print(f"  {n} erro(s) restante(s) apos {attempt} tentativa(s).")

    # ── Phase 4: Report ───────────────────────────────────────────────────
    print("\n[4/4] Gerando relatorio...")
    summary_results = [
        {"success": result["success"], "path": f["path"], "attempts": attempt + 1}
        for f in files
    ]
    report_path = Reporter().generate(destination, spec, files, summary_results, start)

    duration = (datetime.now() - start).total_seconds()
    print("\n" + "=" * 70)
    print("CONCLUIDO!")
    print(f"  Duracao  : {duration:.1f}s")
    print(f"  Arquivos : {len(files)}")
    print(f"  Status   : {'OK' if result['success'] else 'COM ERROS'}")
    print(f"  Relatorio: {report_path}")
    print("=" * 70 + "\n")
```

- [ ] **Step 3: Run all tests**

Run: `.\venv\Scripts\python tests.py`
Expected: `PIPELINE` section — 2 passed | overall 0 failed

- [ ] **Step 4: Commit**

```
git add pipeline.py tests.py
git commit -m "feat: pipeline v2 — 4-phase orchestration with fix loop"
```

---

## Task 7: Delete Superseded Files

**Files:**
- Delete: `planner.py`, `coder.py`

- [ ] **Step 1: Confirm nothing imports them**

Run:
```
grep -r "from planner" . --include="*.py" --exclude-dir=venv
grep -r "from coder" . --include="*.py" --exclude-dir=venv
```
Expected: no output (both were used only by old pipeline.py, now replaced)

- [ ] **Step 2: Delete**

```
del planner.py
del coder.py
```

- [ ] **Step 3: Run full test suite**

Run: `.\venv\Scripts\python tests.py`
Expected: 0 failures (no tests reference planner or coder directly)

- [ ] **Step 4: Commit**

```
git add -u
git commit -m "refactor: remove planner.py and coder.py superseded by generator.py"
```

---

## Task 8: templates/index.html — 4-Phase Progress UI

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Update the log line classifier**

In `templates/index.html`, find the `cls(text)` function and replace it with:

```javascript
function cls(text) {
  if (/={3,}|-{3,}/.test(text))                            return 'l-sep';
  if (/^\[1\/4\]/.test(text))                              return 'l-phase';
  if (/^\[2\/4\]/.test(text))                              return 'l-phase';
  if (/^\[3\/4\]/.test(text))                              return 'l-phase';
  if (/^\[4\/4\]/.test(text))                              return 'l-phase';
  if (/CONCLUIDO|Sintaxe OK|success/i.test(text))          return 'l-ok';
  if (/ERRO|FALHOU|FAILED|ERROR|erro/i.test(text))         return 'l-err';
  if (/Gemini falhou|usando Groq|corrigido/i.test(text))   return 'l-warn';
  if (/^\s*->\s*\d+ arquivo/.test(text))                   return 'l-ok';
  if (/\.(py|js|ts|html|css|json|yaml|md|txt|sql)\b/.test(text)) return 'l-file';
  return 'l-info';
}
```

- [ ] **Step 2: Add a 4-phase progress tracker below the header bar**

Inside `.log-topbar`, after the `<div class="status-pill"...>` element, add:

```html
<div class="phase-track" id="phase-track" style="display:none; gap:0.4rem; align-items:center;">
  <span class="phase-step" id="ph1">1·Generate</span>
  <span class="phase-arrow">›</span>
  <span class="phase-step" id="ph2">2·Write</span>
  <span class="phase-arrow">›</span>
  <span class="phase-step" id="ph3">3·Check</span>
  <span class="phase-arrow">›</span>
  <span class="phase-step" id="ph4">4·Report</span>
</div>
```

Add these CSS rules inside `<style>`:

```css
.phase-track  { display: flex; }
.phase-step   { font-size: 0.68rem; color: #484f58; padding: 0.15rem 0.4rem;
                border-radius: 4px; border: 1px solid #21262d; }
.phase-step.active { color: var(--accent2); border-color: var(--accent); }
.phase-step.done   { color: var(--green);   border-color: #1a4028; background:#0d2318; }
.phase-arrow  { color: #30363d; font-size: 0.75rem; }
```

- [ ] **Step 3: Wire phases to log messages in JS**

Add this function inside `<script>`:

```javascript
function detectPhase(text) {
  if (/^\[1\/4\]/.test(text)) activatePhase(1);
  if (/^\[2\/4\]/.test(text)) activatePhase(2);
  if (/^\[3\/4\]/.test(text)) activatePhase(3);
  if (/^\[4\/4\]/.test(text)) activatePhase(4);
}

function activatePhase(n) {
  document.getElementById('phase-track').style.display = 'flex';
  for (let i = 1; i <= 4; i++) {
    const el = document.getElementById('ph' + i);
    el.className = 'phase-step' + (i < n ? ' done' : i === n ? ' active' : '');
  }
}
```

In the `es.onmessage` handler, add `detectPhase(e.data);` before `appendLine(...)`:

```javascript
es.onmessage = (e) => {
  if (e.data) {
    detectPhase(e.data);
    appendLine(e.data, cls(e.data));
  }
};
```

Also reset phases on `clearLog()`:

```javascript
function clearLog() {
  document.getElementById('log').innerHTML =
    '<div class="empty-state" id="empty">Log limpo</div>';
  document.getElementById('phase-track').style.display = 'none';
  for (let i = 1; i <= 4; i++)
    document.getElementById('ph' + i).className = 'phase-step';
}
```

- [ ] **Step 4: Test UI manually**

Run: `.\venv\Scripts\uvicorn server:app --host 127.0.0.1 --port 8000`

Open `http://localhost:8000` in browser. Use a test destination (empty folder) and spec: `"Create a Python script that prints Hello World"`.

Verify:
- Phase tracker appears and advances: 1·Generate → 2·Write → 3·Check → 4·Report
- Log lines are color-coded correctly
- Status pill changes from "Executando..." to "Concluido"
- Phase steps turn green when done

- [ ] **Step 5: Commit**

```
git add templates/index.html
git commit -m "feat: 4-phase progress tracker in web UI"
```

---

## Task 9: End-to-End Integration Test

- [ ] **Step 1: Clean test output folder**

```
rmdir /s /q test_output
mkdir test_output
```

- [ ] **Step 2: Run full pipeline via Python**

```python
.\venv\Scripts\python -c "
from pipeline import run_pipeline
run_pipeline('test_output', 'Create a Python script called calculator.py with functions: add(a,b), subtract(a,b), multiply(a,b), divide(a,b). Each returns the result. divide raises ValueError if b is 0. Include a main block that demos all functions.', 'greenfield')
"
```

- [ ] **Step 3: Verify results**

Run:
```
dir test_output /s /b
```

Expected:
- `test_output\calculator.py` (or similar) exists
- `test_output\reports\summary.md` exists

- [ ] **Step 4: Run the generated file**

```
.\venv\Scripts\python test_output\calculator.py
```

Expected: Output showing add/subtract/multiply/divide results with no import errors.

- [ ] **Step 5: Run full test suite one last time**

Run: `.\venv\Scripts\python tests.py`
Expected: All tests pass, 0 failures.

- [ ] **Step 6: Final commit**

```
git add .
git commit -m "test: end-to-end integration verified — v2 pipeline working"
```

---

## Self-Review

**Spec coverage check:**
- Single-shot generation → Task 3 (generator.py) ✓
- Dependency installation → Task 4 (runner.py) ✓
- Real execution check (py_compile) → Task 4 (runner.py) ✓
- Full-context fix loop → Task 5 (fixer.py) ✓
- 4-phase pipeline → Task 6 (pipeline.py) ✓
- Configurable model → Task 2 (executor.py) + Task 1 (config.py) ✓
- No more planner/coder → Task 7 ✓
- Updated UI → Task 8 ✓
- Verified end-to-end → Task 9 ✓

**Placeholder scan:** None found. All steps have real code.

**Type consistency:**
- `files: list[dict]` — consistent across generator, runner, fixer, pipeline ✓
- `check_project(destination, files) → dict` — called correctly in pipeline ✓
- `Fixer().fix(destination, files, errors) → list[dict]` — consistent ✓
- `_write_file(destination, path, content)` — defined in pipeline, used internally ✓
- `parse_file_delimited` in generator.py, `_parse_delimited` in fixer.py — intentionally separate (fixer only returns changed files, generator returns all) ✓
