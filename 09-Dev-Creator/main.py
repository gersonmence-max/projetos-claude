import os
import sys
from pathlib import Path


def print_header():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 70)
    print("        DEV CREATOR - Sistema Autonomo de Desenvolvimento")
    print("=" * 70)
    print()


def get_multiline_input():
    print("Opcoes:")
    print("  1. Cole o caminho de um arquivo .txt com o prompt (ex: C:\\prompt.txt)")
    print("  2. Digite o prompt aqui e finalize com Ctrl+Z + Enter")
    print()
    first_line = input().strip()

    if first_line.endswith(".txt") and os.path.isfile(first_line.strip('"').strip("'")):
        path = first_line.strip('"').strip("'")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        print(f"  -> Prompt carregado do arquivo ({len(content)} caracteres)")
        return content

    lines = [first_line]
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def validate_path(path_str):
    path = Path(path_str.strip().strip('"').strip("'"))
    if not path.exists():
        print(f"\nCaminho nao existe: {path}")
        create = input("Criar o diretorio? (s/n): ").strip().lower()
        if create == "s":
            path.mkdir(parents=True, exist_ok=True)
            print("Diretorio criado.")
        else:
            return None
    if path.is_file():
        print(f"\nErro: '{path}' e um arquivo, nao uma pasta.")
        return None
    return str(path)


def detect_project_type(path):
    entries = list(Path(path).iterdir())
    return "greenfield" if not entries else "existing"


def main():
    print_header()

    # CAMPO 1 — Pasta de destino
    print("CAMPO 1 — PASTA DE DESTINO")
    print("-" * 70)
    destination_raw = input("\nCole o caminho da pasta:\n> ").strip()

    if not destination_raw:
        print("Erro: caminho vazio.")
        sys.exit(1)

    destination = validate_path(destination_raw)
    if not destination:
        print("Execucao cancelada.")
        sys.exit(1)

    project_type = detect_project_type(destination)
    label = "Projeto Novo" if project_type == "greenfield" else "Projeto Existente"
    print(f"\nDetectado: {label}")

    # CAMPO 2 — Prompt / Especificacao
    print("\n\nCAMPO 2 — PROMPT / ESPECIFICACAO")
    print("-" * 70 + "\n")
    spec = get_multiline_input()

    if not spec:
        print("Erro: especificacao vazia.")
        sys.exit(1)

    # Resumo antes de executar
    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"  Destino : {destination}")
    print(f"  Tipo    : {label}")
    print(f"  Spec    : {len(spec)} caracteres")
    print()

    confirm = input("Iniciar execucao autonoma? (s/n): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        sys.exit(0)

    from pipeline import run_pipeline
    run_pipeline(destination, spec, project_type)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuario.")
        sys.exit(1)
