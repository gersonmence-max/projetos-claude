# .github/scripts/groq_client.py
import os
from groq import Groq

MODEL = "llama-3.3-70b-versatile"


def gerar_codigo(spec: dict, projeto_txt: str, codigo_atual: str, feedback: str = "") -> str:
    # Critical 1: lazy init — avoid crashing on import when key is absent
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY env var not set")
    client = Groq(api_key=api_key)

    feedback_prefix = ""
    if feedback:
        feedback_prefix = (
            f"REVISÃO ANTERIOR REPROVADA. Feedback: {feedback}\n\n"
            "Corrija os problemas e reimplemente.\n\n"
        )

    # Important 2: spec['arquivos'] may be None — guard before join
    user_msg = (
        f"{feedback_prefix}"
        f"TAREFA: {spec['tarefa']}\n"
        f"DESCRIÇÃO: {spec['descricao']}\n"
        f"ARQUIVOS: {', '.join(spec.get('arquivos') or [])}\n"
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

    # Critical 2: guard against empty choices or None content
    content = r.choices[0].message.content
    if not content:
        raise ValueError("Groq returned empty content")
    return content
