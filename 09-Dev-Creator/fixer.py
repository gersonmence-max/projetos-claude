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
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    pattern = re.compile(
        r"===FILE:\s*(\S+)===\n(.*?)(?=\n===FILE:|\n?===END===|$)",
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
