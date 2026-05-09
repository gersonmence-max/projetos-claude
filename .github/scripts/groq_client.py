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
