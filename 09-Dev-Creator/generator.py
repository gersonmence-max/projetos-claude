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
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    pattern = re.compile(
        r"===FILE:\s*(\S+)===\n(.*?)(?=\n===FILE:|\n?===END===|$)",
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
