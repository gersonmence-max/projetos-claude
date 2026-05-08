import os, sys, time
from pathlib import Path
from datetime import datetime
from groq import Groq

sys.stdout.reconfigure(encoding="utf-8")

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"
PROJETO_DIR = Path("01-SMB-OS")
IGNORAR = {"node_modules", ".git", "__pycache__", "venv", ".venv",
           "dist", "build", ".next", "uv.lock", "pnpm-lock.yaml"}
EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".toml", ".json", ".md"}


def ler_codigo(pasta, max_chars=10000):
    codigo = ""
    for f in sorted(pasta.rglob("*")):
        if any(p in f.parts for p in IGNORAR):
            continue
        if f.suffix not in EXTS:
            continue
        if f.is_file():
            try:
                conteudo = f.read_text(encoding="utf-8", errors="ignore")[:1500]
                bloco = f"\n### {f.relative_to(pasta)}\n```\n{conteudo}\n```\n"
                if len(codigo) + len(bloco) > max_chars:
                    break
                codigo += bloco
            except Exception:
                pass
    return codigo


def chamar_groq(system_prompt, user_msg):
    try:
        r = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=4000,
            temperature=0.1,
        )
        return r.choices[0].message.content
    except Exception as e:
        return f"ERRO: {e}"


projeto_txt = (PROJETO_DIR / "PROJETO.txt").read_text(encoding="utf-8")
codigo_atual = ler_codigo(PROJETO_DIR)

print("=" * 60)
print("Agente Desenvolvedor - SMB-OS")
print("=" * 60)

# Etapa 1: identificar proxima tarefa
proxima = chamar_groq(
    "Voce e um tech lead senior. Analise o PROJETO.txt e o codigo existente. "
    "Identifique UMA tarefa pendente (marcada com []) que seja implementavel agora "
    "com base no que ja existe. Responda APENAS com: "
    "TAREFA: <nome curto>\nDESCRICAO: <o que implementar em 2 frases>\n"
    "ARQUIVOS: <lista de arquivos a criar/modificar, um por linha>",
    f"PROJETO.txt:\n{projeto_txt}\n\nCODIGO EXISTENTE:\n{codigo_atual}",
)
print(f"Proxima tarefa:\n{proxima}")
time.sleep(2)

# Etapa 2: gerar o codigo
codigo_gerado = chamar_groq(
    "Voce e um desenvolvedor senior Full Stack especialista em FastAPI e Next.js. "
    "Implemente a tarefa descrita de forma completa e funcional. "
    "Siga as convencoes do codigo existente. "
    "Responda SOMENTE com blocos no formato:\n"
    "=== ARQUIVO: caminho/relativo ===\n"
    "<conteudo completo>\n"
    "=== FIM ===\n"
    "Gere arquivos reais e completos, nao pseudocodigo.",
    f"TAREFA:\n{proxima}\n\nPROJETO.txt:\n{projeto_txt}\n\nCODIGO EXISTENTE:\n{codigo_atual}",
)

# Salvar arquivos gerados
arquivos_salvos = []
blocos = codigo_gerado.split("=== ARQUIVO:")
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
        print(f"Arquivo gerado: {caminho}")
    except Exception as e:
        print(f"Erro ao salvar: {e}")

# Salvar log
log_dir = Path("sugestoes/01-SMB-OS")
log_dir.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log = log_dir / f"build_{ts}.txt"
log.write_text(
    f"BUILD SESSION - SMB-OS\nData: {datetime.now()}\nModelo: {MODEL}\n\n"
    f"TAREFA:\n{proxima}\n\n"
    f"ARQUIVOS GERADOS:\n" + "\n".join(arquivos_salvos) + "\n\n"
    f"CODIGO:\n{codigo_gerado}",
    encoding="utf-8",
)
print(f"\nLog: {log}")
print(f"Total arquivos gerados: {len(arquivos_salvos)}")
