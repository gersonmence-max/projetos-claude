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
