# .github/scripts/build_smb_os.py
import sys
import re
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
import gemini_client
import groq_client

sys.stdout.reconfigure(encoding="utf-8")

PROJETO_DIR = Path("01-SMB-OS")
IGNORAR = {"node_modules", ".git", "__pycache__", "venv", ".venv",
           "dist", "build", ".next", "uv.lock", "pnpm-lock.yaml"}
EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".sql", ".toml", ".json", ".md"}
MAX_REVISOES = 3


def ler_codigo(pasta, max_chars=10000):
    codigo = ""
    for f in sorted(pasta.rglob("*")):
        if any(p in f.parts for p in IGNORAR):
            continue
        if f.suffix not in EXTS or not f.is_file():
            continue
        try:
            conteudo = f.read_text(encoding="utf-8", errors="ignore")[:1500]
            bloco = f"\n### {f.relative_to(pasta)}\n```\n{conteudo}\n```\n"
            if len(codigo) + len(bloco) > max_chars:
                break
            codigo += bloco
        except Exception:
            pass
    return codigo


def salvar_arquivos(codigo_gerado):
    arquivos_salvos = []
    blocos = codigo_gerado.split("=== ARQUIVO:")
    if len(blocos) > 1:
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
                print(f"  Arquivo gerado: {caminho}")
            except Exception as e:
                print(f"  Erro ao salvar: {e}")
    else:
        pattern = r'(?:(?:#|//|<!--|)\s*([\w/.\-]+\.\w+)\s*(?:-->)?\n)?```(?:\w+)?\n(.*?)```'
        matches = re.findall(pattern, codigo_gerado, re.DOTALL)
        for caminho, conteudo in matches:
            if not caminho or "/" not in caminho:
                continue
            try:
                dest = PROJETO_DIR / caminho.strip()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(conteudo.strip(), encoding="utf-8")
                arquivos_salvos.append(caminho)
                print(f"  Arquivo gerado: {caminho}")
            except Exception as e:
                print(f"  Erro ao salvar: {e}")
    return arquivos_salvos


def main():
    print("=" * 60)
    print("Build SMB-OS — Gemini (arquiteto) + Groq (gerador)")
    print("=" * 60)

    projeto_txt = (PROJETO_DIR / "PROJETO.txt").read_text(encoding="utf-8")
    codigo_atual = ler_codigo(PROJETO_DIR)

    # Passo 1: Gemini planeja
    print("\n[1/4] Gemini planejando tarefa...")
    try:
        spec = gemini_client.planejar(projeto_txt, codigo_atual)
        print(f"  Tarefa: {spec['tarefa']}")
        print(f"  Descrição: {spec['descricao']}")
    except Exception as e:
        print(f"  ERRO no planejamento Gemini: {e}")
        sys.exit(1)

    time.sleep(1)

    # Passo 2: Groq gera
    print("\n[2/4] Groq gerando código...")
    try:
        codigo_gerado = groq_client.gerar_codigo(spec, projeto_txt, codigo_atual)
    except Exception as e:
        print(f"  ERRO na geração Groq: {e}")
        sys.exit(1)

    time.sleep(1)

    # Passo 3: Gemini revisa (máx MAX_REVISOES rodadas)
    status_revisao = "aprovado"
    for tentativa in range(1, MAX_REVISOES + 1):
        print(f"\n[3/4] Gemini revisando (tentativa {tentativa}/{MAX_REVISOES})...")
        try:
            aprovado, feedback = gemini_client.revisar(spec, codigo_gerado)
        except Exception as e:
            print(f"  Erro na revisão (API): {e} — tratando como aprovado")
            aprovado, feedback = True, ""

        if aprovado:
            print("  Código aprovado pelo Gemini")
            status_revisao = "aprovado"
            break

        print(f"  Reprovado. Feedback: {feedback}")
        if tentativa < MAX_REVISOES:
            print("  Groq corrigindo...")
            try:
                codigo_gerado = groq_client.gerar_codigo(
                    spec, projeto_txt, codigo_atual, feedback=feedback
                )
            except Exception as e:
                print(f"  ERRO na correção Groq: {e}")
                sys.exit(1)
            time.sleep(1)
        else:
            status_revisao = f"revisão não aprovada após {MAX_REVISOES} tentativas"
            print(f"  {status_revisao} — commitando mesmo assim")

    # Passo 4: Salvar arquivos
    print("\n[4/4] Salvando arquivos gerados...")
    arquivos_salvos = salvar_arquivos(codigo_gerado)
    if not arquivos_salvos:
        print("  ERRO: nenhum arquivo gerado — abortando commit")
        sys.exit(1)

    log_dir = Path("sugestoes/01-SMB-OS")
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = log_dir / f"build_{ts}.txt"
    log.write_text(
        f"BUILD SESSION — SMB-OS (Gemini+Groq)\n"
        f"Data: {datetime.now()}\n"
        f"Status revisão: {status_revisao}\n\n"
        f"TAREFA:\n{spec}\n\n"
        f"ARQUIVOS GERADOS:\n" + "\n".join(arquivos_salvos) + "\n\n"
        f"CÓDIGO:\n{codigo_gerado}",
        encoding="utf-8",
    )
    print(f"\nLog: {log}")
    print(f"Total arquivos gerados: {len(arquivos_salvos)}")
    print("\nBuild concluído")


if __name__ == "__main__":
    main()
