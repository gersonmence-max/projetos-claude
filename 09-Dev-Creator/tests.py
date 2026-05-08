import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ────────────────────────────────────────────────────────────
# VALIDATOR
# ────────────────────────────────────────────────────────────

def test_validator_valid_python():
    from validator import validate_python
    r = validate_python("def hello():\n    return 'world'")
    assert r == {"valid": True, "error": None}
    print("  [OK] validate_python - codigo valido")

def test_validator_invalid_python():
    from validator import validate_python
    r = validate_python("def broken(:\n    pass")
    assert r["valid"] is False and r["error"] is not None
    print("  [OK] validate_python - codigo invalido detectado")

def test_validator_non_python_always_valid():
    from validator import validate_file
    r = validate_file("README.md", "# qualquer coisa", "markdown")
    assert r == {"valid": True, "error": None}
    print("  [OK] validate_file - markdown sempre valido")

def test_validator_detects_by_extension():
    from validator import validate_file
    r = validate_file("script.py", "def broken(:", "text")
    assert r["valid"] is False
    print("  [OK] validate_file - detecta Python por extensao .py")

def test_validator_empty_python():
    from validator import validate_python
    r = validate_python("")
    assert r["valid"] is True
    print("  [OK] validate_python - arquivo vazio e valido")

# ────────────────────────────────────────────────────────────
# REPORTER
# ────────────────────────────────────────────────────────────

def test_reporter_creates_summary():
    from reporter import Reporter
    with tempfile.TemporaryDirectory() as d:
        r = Reporter()
        path = r.generate(d, "spec", [{"path": "a.py", "description": "x", "language": "python"}],
                          [{"success": True, "path": "a.py", "attempts": 1}], datetime.now())
        assert Path(path).exists()
    print("  [OK] reporter - cria reports/summary.md")

def test_reporter_includes_spec():
    from reporter import Reporter
    with tempfile.TemporaryDirectory() as d:
        r = Reporter()
        path = r.generate(d, "Construir calculadora", [], [], datetime.now())
        assert "Construir calculadora" in Path(path).read_text(encoding="utf-8")
    print("  [OK] reporter - spec aparece no relatorio")

def test_reporter_marks_failed_files():
    from reporter import Reporter
    with tempfile.TemporaryDirectory() as d:
        r = Reporter()
        results = [{"success": False, "path": "bad.py", "attempts": 3, "error": "SyntaxError"}]
        path = r.generate(d, "spec", [{"path": "bad.py", "description": "x", "language": "python"}],
                          results, datetime.now())
        content = Path(path).read_text(encoding="utf-8")
        assert "FAILED" in content and "SyntaxError" in content
    print("  [OK] reporter - marca arquivos que falharam")

def test_reporter_empty_results():
    from reporter import Reporter
    with tempfile.TemporaryDirectory() as d:
        r = Reporter()
        path = r.generate(d, "spec", [], [], datetime.now())
        assert Path(path).exists()
    print("  [OK] reporter - funciona com lista vazia de resultados")

# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────

def test_validate_path_existing_dir():
    from main import validate_path
    with tempfile.TemporaryDirectory() as d:
        assert validate_path(d) == d
    print("  [OK] validate_path - pasta existente retorna caminho")

def test_validate_path_rejects_file():
    from main import validate_path
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        filepath = f.name
    try:
        result = validate_path(filepath)
        assert result is None, "Deveria rejeitar arquivo como destino"
    finally:
        os.unlink(filepath)
    print("  [OK] validate_path - rejeita arquivo (aceita apenas pasta)")

def test_validate_path_strips_quotes():
    from main import validate_path
    with tempfile.TemporaryDirectory() as d:
        assert validate_path(f'"{d}"') == d
    print("  [OK] validate_path - remove aspas do caminho")

def test_detect_greenfield():
    from main import detect_project_type
    with tempfile.TemporaryDirectory() as d:
        assert detect_project_type(d) == "greenfield"
    print("  [OK] detect_project_type - pasta vazia = greenfield")

def test_detect_existing():
    from main import detect_project_type
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "app.py").write_text("x = 1")
        assert detect_project_type(d) == "existing"
    print("  [OK] detect_project_type - pasta com arquivo = existing")

# ────────────────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────────────────

def test_config_has_required_fields():
    from config import config
    for field in ("primary_model", "fallback_model", "max_fix_attempts",
                  "max_files", "max_output_tokens", "google_api_key", "groq_api_key"):
        assert hasattr(config, field), f"Missing field: {field}"
    print("  [OK] config - todos os 7 campos existem")

def test_config_defaults():
    from config import config
    assert config.max_fix_attempts == 3
    assert config.max_files == 50
    assert config.max_output_tokens == 16384
    assert isinstance(config.primary_model, str) and len(config.primary_model) > 0
    assert isinstance(config.fallback_model, str) and len(config.fallback_model) > 0
    print("  [OK] config - defaults corretos")

# ────────────────────────────────────────────────────────────
# EXECUTOR
# ────────────────────────────────────────────────────────────

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

# ────────────────────────────────────────────────────────────
# GENERATOR
# ────────────────────────────────────────────────────────────

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

def test_parse_file_delimited_crlf():
    from generator import parse_file_delimited
    raw = "===FILE: main.py===\r\nprint('hi')\r\n===FILE: b.py===\r\ny = 2\r\n===END==="
    files = parse_file_delimited(raw)
    assert len(files) == 2
    assert files[0]["path"] == "main.py"
    print("  [OK] parse_file_delimited - lida com line endings CRLF")

# ────────────────────────────────────────────────────────────
# RUNNER
# ────────────────────────────────────────────────────────────

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

# ────────────────────────────────────────────────────────────
# FIXER
# ────────────────────────────────────────────────────────────

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

SECTIONS = {
    "VALIDATOR": [
        test_validator_valid_python,
        test_validator_invalid_python,
        test_validator_non_python_always_valid,
        test_validator_detects_by_extension,
        test_validator_empty_python,
    ],
    "REPORTER": [
        test_reporter_creates_summary,
        test_reporter_includes_spec,
        test_reporter_marks_failed_files,
        test_reporter_empty_results,
    ],
    "MAIN": [
        test_validate_path_existing_dir,
        test_validate_path_rejects_file,
        test_validate_path_strips_quotes,
        test_detect_greenfield,
        test_detect_existing,
    ],
    "CONFIG": [
        test_config_has_required_fields,
        test_config_defaults,
    ],
    "EXECUTOR": [
        test_executor_uses_config_model,
        test_executor_accepts_custom_model,
    ],
    "GENERATOR": [
        test_parse_file_delimited_basic,
        test_parse_file_delimited_no_end_marker,
        test_parse_file_delimited_empty_returns_empty,
        test_parse_file_delimited_preserves_content_with_quotes,
        test_generator_raises_on_empty_response,
        test_generator_raises_on_executor_failure,
        test_generator_enforces_max_files,
        test_parse_file_delimited_crlf,
    ],
    "RUNNER": [
        test_install_dependencies_no_requirements,
        test_install_dependencies_with_file,
        test_check_python_syntax_valid,
        test_check_python_syntax_invalid,
        test_check_project_success,
        test_check_project_failure,
    ],
    "FIXER": [
        test_build_context_reads_files,
        test_build_context_multiple_files,
        test_fixer_returns_empty_on_executor_failure,
        test_fixer_returns_only_changed_files,
    ],
    "PIPELINE": [
        test_pipeline_calls_all_four_phases,
        test_pipeline_runs_fixer_on_errors,
    ],
}


def run_all():
    print("\n" + "=" * 60)
    print("  DEV CREATOR - TEST SUITE")
    print("=" * 60)
    passed = failed = 0

    for section, tests in SECTIONS.items():
        print(f"\n[{section}]")
        for test in tests:
            try:
                test()
                passed += 1
            except AssertionError as e:
                failed += 1
                print(f"  [FALHOU] {test.__name__}: {e}")
            except Exception as e:
                failed += 1
                print(f"  [ERRO]   {test.__name__}: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print(f"  RESULTADO: {passed} passou | {failed} falhou")
    print("=" * 60 + "\n")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_all()
