#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📝 ANALISADOR DE SUGESTÕES DE MELHORIA
Sistema escalável que funciona com 13, 50, 100 ou qualquer número de projetos.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

class AnalisadorSugestoes:
    """Analisa código de projetos e gera sugestões de melhoria"""

    def __init__(self, pasta_projetos: str):
        self.pasta_projetos = Path(pasta_projetos)
        self.pasta_sugestoes = self.pasta_projetos / "sugestoes"
        self.pasta_sugestoes.mkdir(exist_ok=True)

        self.projetos_encontrados = 0
        self.sugestoes_totais = 0
        self.sugestoes_por_projeto = {}

    # ========================================================================
    # DESCOBERTA DINÂMICA DE PROJETOS (escalável para qualquer quantidade)
    # ========================================================================

    def descobrir_projetos(self) -> List[Path]:
        """
        Descobre QUALQUER número de projetos (13, 50, 100+).
        Qualquer pasta com PROJETO.txt é um projeto válido.
        """
        projetos = []

        if not self.pasta_projetos.exists():
            print(f"❌ Pasta não encontrada: {self.pasta_projetos}")
            return projetos

        # Iterar todas as pastas
        for item in sorted(self.pasta_projetos.iterdir()):
            if not item.is_dir():
                continue

            projeto_txt = item / "PROJETO.txt"
            if projeto_txt.exists():
                projetos.append(item)
                self.projetos_encontrados += 1

        print(f"✅ Descobertos {self.projetos_encontrados} projetos")
        return projetos

    # ========================================================================
    # ANÁLISE DE CÓDIGO (reutilizável para qualquer projeto)
    # ========================================================================

    def analisar_projeto(self, projeto_path: Path) -> List[Dict]:
        """Analisa UM projeto e retorna sugestões"""
        sugestoes = []
        src_dir = projeto_path / "src"

        if not src_dir.exists():
            return sugestoes

        # Lê TODOS os arquivos Python (escalável)
        for arquivo_py in src_dir.glob("**/*.py"):
            try:
                conteudo = arquivo_py.read_text(encoding="utf-8", errors="ignore")
                caminho_relativo = arquivo_py.relative_to(src_dir)

                # Verificações de padrões
                sugestoes.extend(self._check_cache(conteudo, caminho_relativo))
                sugestoes.extend(self._check_n_plus_1(conteudo, caminho_relativo))
                sugestoes.extend(self._check_error_handling(conteudo, caminho_relativo))
                sugestoes.extend(self._check_sql_injection(conteudo, caminho_relativo))
                sugestoes.extend(self._check_logging(conteudo, caminho_relativo))
                sugestoes.extend(self._check_validation(conteudo, caminho_relativo))
                sugestoes.extend(self._check_async_code(conteudo, caminho_relativo))

            except Exception as e:
                # Silenciosamente ignorar erros de leitura
                pass

        # Verificar se há testes
        tests_dir = src_dir / "tests"
        if not tests_dir.exists() or not list(tests_dir.glob("test_*.py")):
            sugestoes.append({
                "titulo": "Adicionar Testes Automatizados",
                "arquivo": "tests/",
                "tipo": "Qualidade",
                "severidade": "ALTA",
                "descricao": "Não há testes automatizados. Impossível refatorar com segurança.",
                "beneficio": "Confiança para fazer mudanças sem medo",
                "esforco": "Médio (5-8 horas)"
            })

        # Remover duplicatas
        sugestoes = self._remover_duplicatas(sugestoes)

        return sugestoes

    # ========================================================================
    # VERIFICAÇÕES DE PADRÕES (reutilizáveis)
    # ========================================================================

    def _check_cache(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta funções que deveriam usar cache"""
        sugestoes = []

        # Padrão: função get_* com db.query
        if re.search(r'def get_\w+.*?:\n.*?db\.query', conteudo, re.DOTALL):
            if "cache" not in conteudo and "redis" not in conteudo:
                sugestoes.append({
                    "titulo": "Implementar Cache para Queries Repetidas",
                    "arquivo": str(arquivo),
                    "tipo": "Performance",
                    "severidade": "ALTA",
                    "descricao": "Função faz queries ao banco repetidamente. Cada query = 100ms. Com cache = 1ms.",
                    "beneficio": "⚡ 10-100x mais rápido | 💰 Menos load no DB | 📈 Suportar 10x mais usuários",
                    "esforco": "Médio (4-6 horas)",
                    "implementacao": "Adicionar Redis/Memcached + cache invalidation"
                })

        return sugestoes

    def _check_n_plus_1(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta N+1 query problem"""
        sugestoes = []

        # Padrão: loop com query inside
        if re.search(r'for .* in .*?:\n.*?db\.query', conteudo, re.DOTALL):
            if "joinedload" not in conteudo and "prefetch_related" not in conteudo:
                sugestoes.append({
                    "titulo": "Otimizar N+1 Query Problem",
                    "arquivo": str(arquivo),
                    "tipo": "Performance",
                    "severidade": "CRÍTICA",
                    "descricao": "Loop com query inside. 1 query + N mais queries. Com 100 usuários = 101 queries!",
                    "beneficio": "⚡ 100x mais rápido | 💰 Reduz DB load drasticamente | 🚀 Escalável",
                    "esforco": "Pequeno (1-2 horas)",
                    "implementacao": "Usar joinedload() ou prefetch_related()"
                })

        return sugestoes

    def _check_error_handling(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta falta de error handling"""
        sugestoes = []

        # Padrão: função com @app.route ou def mas sem try/except
        if re.search(r'(@app\.(route|get|post)|async def) .+?:', conteudo):
            if "try:" not in conteudo or conteudo.count("try:") < 3:
                sugestoes.append({
                    "titulo": "Melhorar Error Handling em Endpoints",
                    "arquivo": str(arquivo),
                    "tipo": "Confiabilidade",
                    "severidade": "ALTA",
                    "descricao": "Endpoints sem try/except. Exceções não tratadas = erro 500 genérico.",
                    "beneficio": "🛡️ Segurança (não expõe stack trace) | 📊 Logs úteis | 👤 Melhor UX",
                    "esforco": "Pequeno (2-3 horas)",
                    "implementacao": "Adicionar try/except com status codes apropriados (409, 403, etc)"
                })

        return sugestoes

    def _check_sql_injection(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta SQL injection risks"""
        sugestoes = []

        # Padrão: f-strings em SQL
        if re.search(r'(f["\']SELECT|f["\']INSERT|f["\']UPDATE|f["\']DELETE)', conteudo):
            if "?" not in conteudo and "%s" not in conteudo:
                sugestoes.append({
                    "titulo": "🚨 CRÍTICO: SQL Injection Risk",
                    "arquivo": str(arquivo),
                    "tipo": "Segurança",
                    "severidade": "CRÍTICA",
                    "descricao": "SQL com f-strings. Atacante pode injetar SQL malicioso.",
                    "beneficio": "🔒 Elimina vulnerabilidade crítica | 🛡️ Código seguro",
                    "esforco": "Pequeno (1-2 horas)",
                    "implementacao": "Usar prepared statements com ? ou %s"
                })

        return sugestoes

    def _check_logging(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta falta de logging estruturado"""
        sugestoes = []

        if "print(" in conteudo and "logging" not in conteudo:
            num_prints = conteudo.count("print(")
            if num_prints > 3:
                sugestoes.append({
                    "titulo": "Implementar Logging Estruturado",
                    "arquivo": str(arquivo),
                    "tipo": "Confiabilidade",
                    "severidade": "MÉDIA",
                    "descricao": f"Arquivo usa {num_prints} print() statements. Em produção, prints são perdidos.",
                    "beneficio": "📊 Logs estruturados | 🔍 Fácil debugging | 📈 Monitoramento",
                    "esforco": "Pequeno (1-2 horas)",
                    "implementacao": "Substituir print() por logging.info/error"
                })

        return sugestoes

    def _check_validation(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta falta de validação de entrada"""
        sugestoes = []

        if "def " in conteudo and "request" in conteudo:
            if "validate" not in conteudo and "schema" not in conteudo:
                sugestoes.append({
                    "titulo": "Adicionar Validação de Entrada (Schemas)",
                    "arquivo": str(arquivo),
                    "tipo": "Segurança",
                    "severidade": "MÉDIA",
                    "descricao": "Endpoint recebe dados sem validar. Dados inválidos = bugs ou segurança fraca.",
                    "beneficio": "🔒 Segurança | 📊 Dados confiáveis | 👤 Melhor UX",
                    "esforco": "Médio (2-4 horas)",
                    "implementacao": "Usar Pydantic ou similar para validação de schemas"
                })

        return sugestoes

    def _check_async_code(self, conteudo: str, arquivo: Path) -> List[Dict]:
        """Detecta código que deveria ser async"""
        sugestoes = []

        # Se tem requests.get ou similar em função regular (não async)
        if ("requests.get" in conteudo or "requests.post" in conteudo) and "async def" not in conteudo:
            sugestoes.append({
                "titulo": "Considerar Usar Async para Operações I/O",
                "arquivo": str(arquivo),
                "tipo": "Performance",
                "severidade": "MÉDIA",
                "descricao": "Operações I/O bloqueantes (HTTP, DB) em código síncrono. Cada operação bloqueia a thread.",
                "beneficio": "⚡ Suportar 10x mais requisições simultâneas | 📈 Melhor escalabilidade",
                "esforso": "Médio (3-5 horas)",
                "implementacao": "Converter para async/await com aiohttp ou similar"
            })

        return sugestoes

    def _remover_duplicatas(self, sugestoes: List[Dict]) -> List[Dict]:
        """Remove sugestões duplicadas"""
        seen = set()
        unique = []

        for sug in sugestoes:
            key = sug["titulo"]
            if key not in seen:
                seen.add(key)
                unique.append(sug)

        return unique

    # ========================================================================
    # GERAÇÃO DE ARQUIVO TXT (por projeto)
    # ========================================================================

    def gerar_arquivo_sugestoes(self, nome_projeto: str, sugestoes: List[Dict]):
        """Gera arquivo TXT com sugestões para UM projeto"""

        if not sugestoes:
            return

        # Ordenar por severidade
        ordem_severidade = {"CRÍTICA": 0, "ALTA": 1, "MÉDIA": 2}
        sugestoes = sorted(
            sugestoes,
            key=lambda x: ordem_severidade.get(x.get("severidade", "MÉDIA"), 3)
        )

        conteudo = f"""{'='*80}
📋 SUGESTÕES DE MELHORIA - {nome_projeto}
{'='*80}

Analisado: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Total de sugestões: {len(sugestoes)}

{'='*80}
"""

        for idx, sug in enumerate(sugestoes, 1):
            severidade = sug.get("severidade", "MÉDIA")
            icon = "🔴" if severidade == "CRÍTICA" else "🟠" if severidade == "ALTA" else "🟡"

            conteudo += f"""
SUGESTÃO #{idx}: {sug.get('titulo', 'Sem título')}
{'─'*80}

{icon} SEVERIDADE: {severidade}
📁 ARQUIVO: {sug.get('arquivo', 'N/A')}
🏷️  TIPO: {sug.get('tipo', 'Geral')}

DESCRIÇÃO:
{sug.get('descricao', 'N/A')}

BENEFÍCIO:
{sug.get('beneficio', 'N/A')}

ESFORÇO: {sug.get('esforco', 'Desconhecido')}

IMPLEMENTAÇÃO:
{sug.get('implementacao', 'Veja com Claude')}

"""

        conteudo += f"""
{'='*80}
RESUMO

Total de sugestões: {len(sugestoes)}
- Críticas: {sum(1 for s in sugestoes if s.get('severidade') == 'CRÍTICA')}
- Altas: {sum(1 for s in sugestoes if s.get('severidade') == 'ALTA')}
- Médias: {sum(1 for s in sugestoes if s.get('severidade') == 'MÉDIA')}

PRÓXIMOS PASSOS:
1. ✅ Leia esta sugestões quando tiver tempo
2. ✅ Se gostar de uma → abra com Claude
3. ✅ Claude gera código → você substitui arquivo
4. ✅ Teste e confirme que continua funcionando

{'='*80}
"""

        # Salvar arquivo
        arquivo_saida = self.pasta_sugestoes / f"{nome_projeto}.txt"
        arquivo_saida.write_text(conteudo, encoding="utf-8")

        self.sugestoes_por_projeto[nome_projeto] = len(sugestoes)
        self.sugestoes_totais += len(sugestoes)

        print(f"  ✅ {nome_projeto}: {len(sugestoes)} sugestões")

    # ========================================================================
    # GERAR ÍNDICE (resumo de todos os projetos)
    # ========================================================================

    def gerar_indice(self):
        """Gera arquivo INDICE.txt com resumo de todos"""

        conteudo = f"""{'='*80}
📊 ÍNDICE DE SUGESTÕES DE MELHORIA
{'='*80}

Gerado: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Projetos analisados: {self.projetos_encontrados}

{'─'*80}
PROJETOS COM SUGESTÕES
{'─'*80}

"""

        if not self.sugestoes_por_projeto:
            conteudo += "\n✅ Todos os projetos estão bons!\n"
        else:
            for projeto, num_sug in sorted(
                self.sugestoes_por_projeto.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                conteudo += f"  📝 {projeto}: {num_sug} sugestões\n"

        conteudo += f"""

{'─'*80}
RESUMO GERAL
{'─'*80}

Total de sugestões geradas: {self.sugestoes_totais}
Projetos com sugestões: {len(self.sugestoes_por_projeto)}
Projetos sem problemas: {self.projetos_encontrados - len(self.sugestoes_por_projeto)}

{'─'*80}
PRÓXIMAS AÇÕES
{'─'*80}

1. 📖 Abra pasta: sugestoes/
2. 📝 Leia os .txt dos projetos com sugestões
3. 💬 Se gostar de uma sugestão:
   - Copie o texto
   - Abra com Claude
   - Peça: "Implemente isso"
   - Claude gera código
   - Você substitui o arquivo

{'='*80}
"""

        arquivo_indice = self.pasta_sugestoes / "INDICE.txt"
        arquivo_indice.write_text(conteudo, encoding="utf-8")

        print(f"\n✅ Índice gerado: {arquivo_indice}")

    # ========================================================================
    # EXECUÇÃO PRINCIPAL (escalável para qualquer quantidade)
    # ========================================================================

    def executar(self):
        """Executa análise de TODOS os projetos (n, 13, 50, 100+)"""

        print("\n" + "="*80)
        print("📝 ANALISADOR DE SUGESTÕES - MULTI-PROJETO")
        print("="*80 + "\n")

        # Descobrir projetos
        projetos = self.descobrir_projetos()

        if not projetos:
            print("❌ Nenhum projeto encontrado")
            return

        # Analisar cada projeto
        print(f"\nAnalisando {len(projetos)} projetos...\n")

        for projeto_path in projetos:
            print(f"  🔍 {projeto_path.name}...", end="", flush=True)
            sugestoes = self.analisar_projeto(projeto_path)

            if sugestoes:
                print(f" {len(sugestoes)} sugestões", end="")
                self.gerar_arquivo_sugestoes(projeto_path.name, sugestoes)
            else:
                print(" ✅ OK (sem problemas)", end="")

            print()

        # Gerar índice
        print("\n" + "-"*80)
        self.gerar_indice()

        # Resumo final
        print("\n" + "="*80)
        print("✅ ANÁLISE CONCLUÍDA")
        print("="*80)
        print(f"Projetos analisados: {self.projetos_encontrados}")
        print(f"Sugestões geradas: {self.sugestoes_totais}")
        print(f"Pasta de sugestões: {self.pasta_sugestoes}")
        print("="*80 + "\n")

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    pasta_projetos = r"C:\Users\g-fil\Documents\Projetos Claude\projetos-organizados"
    analisador = AnalisadorSugestoes(pasta_projetos)
    analisador.executar()

if __name__ == "__main__":
    main()
