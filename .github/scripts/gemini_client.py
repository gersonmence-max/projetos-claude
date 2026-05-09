# .github/scripts/gemini_client.py
import os
import json
from google import genai

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


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var not set")
    return genai.Client(api_key=api_key)


def planejar(projeto_txt: str, codigo: str) -> dict:
    """
    Lê PROJETO.txt + código e retorna spec da próxima tarefa.
    Retorna: {"tarefa": str, "descricao": str, "arquivos": [str], "estrutura_sugerida": str}
    """
    client = _get_client()
    prompt = (
        "Você é um tech lead senior. Analise o PROJETO.txt e o código existente. "
        "Identifique UMA tarefa pendente (marcada com []) que seja implementável agora "
        "com base no que já existe. Responda APENAS em JSON válido com este formato:\n"
        '{"tarefa": "<nome curto>", "descricao": "<o que implementar em 2 frases>", '
        '"arquivos": ["<arquivo1>", "<arquivo2>"], '
        '"estrutura_sugerida": "<estrutura do código em 3-5 linhas>"}\n\n'
        f"PROJETO.txt:\n{projeto_txt}\n\nCÓDIGO EXISTENTE:\n{codigo}"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    if not response.text:
        raise ValueError("Gemini returned empty response in planejar()")
    return _parse_json(response.text)


def revisar(spec: dict, codigo_gerado: str) -> tuple[bool, str]:
    """
    Revisa o código gerado contra a spec.
    Retorna: (aprovado: bool, feedback: str)
    """
    client = _get_client()
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
    response = client.models.generate_content(model=MODEL, contents=prompt)
    if not response.text:
        raise ValueError("Gemini returned empty response in revisar()")
    result = _parse_json(response.text)
    aprovado = result.get("aprovado")
    if aprovado is None:
        raise ValueError(f"Gemini response missing 'aprovado' key: {result}")
    return bool(aprovado), result.get("feedback", "")
