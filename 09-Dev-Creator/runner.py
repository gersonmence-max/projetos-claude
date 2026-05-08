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
