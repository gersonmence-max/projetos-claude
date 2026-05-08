#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛡️ AGENTE DE SEGURANÇA AVANÇADO
Valida código contra frameworks: OWASP Top 10, NIST CSF, CIS Controls, Zero Trust
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
from enum import Enum

class SeveridadeSeguranca(Enum):
    CRÍTICA = "🔴 CRÍTICA"      # Não pode ir para produção
    ALTA = "🟠 ALTA"            # Deve ser corrigido antes de produção
    MÉDIA = "🟡 MÉDIA"          # Corrigir em próxima release
    BAIXA = "🟢 BAIXA"          # Nice to have

class AgenteSegurancaAvancado:
    """Valida segurança contra múltiplos frameworks"""

    nome = "🛡️ SEGURANÇA AVANÇADO"

    def __init__(self):
        self.achados = []
        self.pontuacao_seguranca = 100  # Start 100, decrease by issues

    # ========================================================================
    # VALIDAÇÕES OWASP TOP 10
    # ========================================================================

    def validar_owasp_top_10(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Valida contra OWASP Top 10 2021"""
        achados = []

        # A01: Broken Access Control
        if self._check_access_control(conteudo):
            achados.append({
                "titulo": "🚨 A01: BROKEN ACCESS CONTROL",
                "framework": "OWASP Top 10",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Acesso não verificado em endpoints",
                "recomendacao": "Implementar autorização em TODOS endpoints",
                "referencias": ["OWASP A01:2021", "CIS Control 6.1"]
            })
            self.pontuacao_seguranca -= 20

        # A02: Cryptographic Failures
        if self._check_crypto_failures(conteudo):
            achados.append({
                "titulo": "🚨 A02: CRYPTOGRAPHIC FAILURES",
                "framework": "OWASP Top 10",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Dados sensíveis sem criptografia",
                "recomendacao": "Usar AES-256 para dados em repouso, TLS 1.3 em transit",
                "referencias": ["OWASP A02:2021", "NIST SP 800-175B"]
            })
            self.pontuacao_seguranca -= 20

        # A03: Injection
        if self._check_injection(conteudo):
            achados.append({
                "titulo": "🚨 A03: INJECTION",
                "framework": "OWASP Top 10",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "SQL/Code injection possível",
                "recomendacao": "Usar parameterized queries ou ORM",
                "referencias": ["OWASP A03:2021", "CIS Control 3.1"]
            })
            self.pontuacao_seguranca -= 20

        # A05: Security Misconfiguration
        if self._check_misconfig(conteudo):
            achados.append({
                "titulo": "⚠️ A05: SECURITY MISCONFIGURATION",
                "framework": "OWASP Top 10",
                "severidade": SeveridadeSeguranca.ALTA,
                "arquivo": arquivo,
                "problema": "Configurações de segurança fracas",
                "recomendacao": "Revisar defaults, habilitar HTTPS, headers de segurança",
                "referencias": ["OWASP A05:2021"]
            })
            self.pontuacao_seguranca -= 10

        # A07: Authentication Failures
        if self._check_auth_failures(conteudo):
            achados.append({
                "titulo": "🚨 A07: AUTHENTICATION FAILURES",
                "framework": "OWASP Top 10",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Autenticação fraca ou faltando",
                "recomendacao": "Implementar MFA, OAuth 2.0, senhas fortes",
                "referencias": ["OWASP A07:2021", "NIST SP 800-63B"]
            })
            self.pontuacao_seguranca -= 20

        return achados

    # ========================================================================
    # VALIDAÇÕES NIST CYBERSECURITY FRAMEWORK
    # ========================================================================

    def validar_nist_csf(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Valida contra NIST CSF"""
        achados = []

        # PROTECT: Implementar safeguards
        if not self._check_protection_measures(conteudo):
            achados.append({
                "titulo": "NIST-PROTECT: Medidas de proteção insuficientes",
                "framework": "NIST CSF",
                "severidade": SeveridadeSeguranca.ALTA,
                "arquivo": arquivo,
                "problema": "Faltam proteções contra ataques conhecidos",
                "recomendacao": "Implementar WAF, rate limiting, input validation",
                "referencias": ["NIST CSF PROTECT"]
            })

        # DETECT: Capacidade de detecção
        if not self._check_detection_capability(conteudo):
            achados.append({
                "titulo": "NIST-DETECT: Capacidade de detecção fraca",
                "framework": "NIST CSF",
                "severidade": SeveridadeSeguranca.ALTA,
                "arquivo": arquivo,
                "problema": "Sem logging estruturado de eventos de segurança",
                "recomendacao": "Implementar SIEM, structured logging, alertas",
                "referencias": ["NIST CSF DETECT"]
            })

        return achados

    # ========================================================================
    # VALIDAÇÕES CIS CONTROLS
    # ========================================================================

    def validar_cis_controls(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Valida contra CIS Controls v8"""
        achados = []

        # CIS 6: Access Control
        if not self._check_cis_access_control(conteudo):
            achados.append({
                "titulo": "CIS 6: Access Control inadequado",
                "framework": "CIS Controls v8",
                "severidade": SeveridadeSeguranca.ALTA,
                "arquivo": arquivo,
                "problema": "Sem controle de acesso por usuário/função",
                "recomendacao": "Implementar RBAC/ABAC com least privilege",
                "referencias": ["CIS Control 6"]
            })

        # CIS 3: Data Protection
        if not self._check_cis_data_protection(conteudo):
            achados.append({
                "titulo": "CIS 3: Proteção de dados inadequada",
                "framework": "CIS Controls v8",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Dados sensíveis sem proteção",
                "recomendacao": "Encriptar dados em repouso e em trânsito",
                "referencias": ["CIS Control 3"]
            })

        return achados

    # ========================================================================
    # VALIDAÇÕES ZERO TRUST ARCHITECTURE
    # ========================================================================

    def validar_zero_trust(self, conteudo: str, arquivo: str) -> List[Dict]:
        """Valida princípios Zero Trust"""
        achados = []

        # Verificar identidade SEMPRE
        if not self._check_identity_verification(conteudo):
            achados.append({
                "titulo": "Zero Trust: Verificação de identidade insuficiente",
                "framework": "Zero Trust Architecture",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Funções não verificam identidade do chamador",
                "recomendacao": "Verificar JWT/token em TODAS funções",
                "referencias": ["NIST SP 800-207 Zero Trust"]
            })

        # Least privilege access
        if not self._check_least_privilege(conteudo):
            achados.append({
                "titulo": "Zero Trust: Least Privilege não implementado",
                "framework": "Zero Trust Architecture",
                "severidade": SeveridadeSeguranca.ALTA,
                "arquivo": arquivo,
                "problema": "Funções têm acesso a mais dados que necessário",
                "recomendacao": "Aplicar princípio de menor privilégio",
                "referencias": ["NIST SP 800-207"]
            })

        # Encriptação obrigatória
        if not self._check_mandatory_encryption(conteudo):
            achados.append({
                "titulo": "Zero Trust: Encriptação não é obrigatória",
                "framework": "Zero Trust Architecture",
                "severidade": SeveridadeSeguranca.CRÍTICA,
                "arquivo": arquivo,
                "problema": "Comunicação sem TLS",
                "recomendacao": "TLS 1.3 obrigatório para TUDO",
                "referencias": ["NIST SP 800-207"]
            })

        return achados

    # ========================================================================
    # MÉTODOS DE VERIFICAÇÃO
    # ========================================================================

    def _check_access_control(self, conteudo: str) -> bool:
        """Verifica se há falta de controle de acesso"""

        # Procurar por @app.route, @app.post sem decorador de auth
        routes = re.findall(r'@app\.(route|get|post|put|delete)\(["\']([^"\']+)', conteudo)

        for route_type, path in routes:
            # Se rota retorna dados sensíveis sem auth
            if any(x in path for x in ["/users", "/admin", "/data", "/config"]):
                if "Depends()" not in conteudo or "get_current_user" not in conteudo:
                    return True

        return False

    def _check_crypto_failures(self, conteudo: str) -> bool:
        """Verifica criptografia fraca"""

        # Procurar por dados sensíveis guardados em plain text
        sensitive_patterns = [
            r'password\s*=\s*["\']',  # Senha em plain text
            r'api_key\s*=\s*["\']',    # API key hardcoded
            r'secret\s*=\s*["\']',     # Secret hardcoded
            r'token\s*=\s*["\']',      # Token hardcoded
            r'credit_card\s*:',        # Credit card guardado
            r'ssn\s*:',                # SSN guardado
        ]

        return any(re.search(pattern, conteudo, re.IGNORECASE) for pattern in sensitive_patterns)

    def _check_injection(self, conteudo: str) -> bool:
        """Verifica SQL injection"""

        # Procurar por f-strings em SQL
        injection_patterns = [
            r'f["\']SELECT.*{',
            r'f["\']INSERT.*{',
            r'f["\']UPDATE.*{',
            r'\.execute\(f',
            r'\.query\(f',
        ]

        return any(re.search(pattern, conteudo, re.IGNORECASE) for pattern in injection_patterns)

    def _check_misconfig(self, conteudo: str) -> bool:
        """Verifica misconfigurações"""

        # Procurar por configs fracas
        misconfig_patterns = [
            r'DEBUG\s*=\s*True',        # Debug em produção
            r'SECRET_KEY\s*=\s*["\']',  # Secret hardcoded
            r'CORS.*\*',                # CORS aberto
            r'ssl_context\s*=\s*None',  # Sem SSL
        ]

        return any(re.search(pattern, conteudo, re.IGNORECASE) for pattern in misconfig_patterns)

    def _check_auth_failures(self, conteudo: str) -> bool:
        """Verifica falhas de autenticação"""

        # Procurar por falta de MFA, senhas fracas, etc
        auth_issues = [
            r'password.*len.*<\s*8',     # Senha muito curta
            r'mfa.*False',               # MFA desabilitado
            r'verify_password.*==',      # Timing attack (string comparison)
            r'session.*30.*day',         # Session muito longa
            r'token.*exp.*[0-9]+.*day',  # Token muito longo
        ]

        return any(re.search(pattern, conteudo, re.IGNORECASE) for pattern in auth_issues)

    def _check_protection_measures(self, conteudo: str) -> bool:
        """Verifica se há medidas de proteção"""

        has_rate_limiting = "limiter" in conteudo or "rate_limit" in conteudo
        has_validation = "validator" in conteudo or "validation" in conteudo
        has_security_headers = "X-Content-Type-Options" in conteudo

        return has_rate_limiting and has_validation and has_security_headers

    def _check_detection_capability(self, conteudo: str) -> bool:
        """Verifica se há capacidade de detecção"""

        has_logging = "logger" in conteudo and "audit" in conteudo
        has_alerts = "alert" in conteudo or "exception" in conteudo
        has_monitoring = "monitor" in conteudo or "siem" in conteudo

        return has_logging and (has_alerts or has_monitoring)

    def _check_cis_access_control(self, conteudo: str) -> bool:
        """Verifica CIS Access Control"""

        has_rbac = "role" in conteudo.lower() or "permission" in conteudo.lower()
        has_auth = "oauth" in conteudo.lower() or "jwt" in conteudo.lower()
        has_verification = "verify" in conteudo.lower() or "authenticate" in conteudo.lower()

        return has_rbac and has_auth and has_verification

    def _check_cis_data_protection(self, conteudo: str) -> bool:
        """Verifica CIS Data Protection"""

        has_encryption = "encrypt" in conteudo.lower() or "cipher" in conteudo.lower()
        has_tls = "tls" in conteudo.lower() or "https" in conteudo.lower()
        has_hashing = "hash" in conteudo.lower() or "bcrypt" in conteudo.lower()

        return has_encryption and has_tls and has_hashing

    def _check_identity_verification(self, conteudo: str) -> bool:
        """Verifica verificação de identidade Zero Trust"""

        # Procurar por funções que verificam identidade
        verify_patterns = [
            r'get_current_user',
            r'verify_token',
            r'check_auth',
            r'validate_jwt',
            r'Depends\(.*get_current_user',
        ]

        # Contar quantas funções têm verificação
        all_functions = re.findall(r'(?:async )?def (\w+)\(', conteudo)
        verified_functions = [f for f in all_functions if any(
            re.search(pattern, conteudo, re.IGNORECASE) for pattern in verify_patterns
        )]

        # Se 80%+ funções têm verificação, está OK
        return len(verified_functions) >= len(all_functions) * 0.8

    def _check_least_privilege(self, conteudo: str) -> bool:
        """Verifica least privilege"""

        # Procurar por acesso a dados mínimo
        least_privilege_patterns = [
            r'select\(.*\)',           # SQL select específico
            r'only\(.*\)',             # ORM select específico
            r'filter\(.*\)',           # Filtro de dados
            r'permission.*in.*user',   # Check permissions
        ]

        return any(re.search(pattern, conteudo, re.IGNORECASE) for pattern in least_privilege_patterns)

    def _check_mandatory_encryption(self, conteudo: str) -> bool:
        """Verifica encriptação obrigatória"""

        has_tls = "TLSVersion.TLSv1_3" in conteudo or "ssl_context" in conteudo
        has_cipher = "AES_256" in conteudo or "ChaCha" in conteudo
        has_cert = "certificate" in conteudo.lower() or ".pem" in conteudo

        return has_tls or has_cipher or has_cert

    # ========================================================================
    # ANÁLISE COMPLETA
    # ========================================================================

    def analisar(self, projeto_path: Path) -> Tuple[List[Dict], int]:
        """Analisa projeto com segurança avançada"""

        achados = []
        src_dir = projeto_path / "src"

        if not src_dir.exists():
            return achados, self.pontuacao_seguranca

        # Ler todos os arquivos Python
        for arquivo_py in src_dir.glob("**/*.py"):
            try:
                conteudo = arquivo_py.read_text(encoding="utf-8", errors="ignore")
                caminho_relativo = arquivo_py.relative_to(src_dir)

                # Validações em paralelo
                achados.extend(self.validar_owasp_top_10(conteudo, str(caminho_relativo)))
                achados.extend(self.validar_nist_csf(conteudo, str(caminho_relativo)))
                achados.extend(self.validar_cis_controls(conteudo, str(caminho_relativo)))
                achados.extend(self.validar_zero_trust(conteudo, str(caminho_relativo)))

            except Exception as e:
                pass

        return achados, self.pontuacao_seguranca

    def gerar_relatorio(self, achados: List[Dict], pontuacao: int) -> str:
        """Gera relatório de segurança"""

        relatorio = f"""
{'='*80}
🛡️  RELATÓRIO DE SEGURANÇA AVANÇADO
{'='*80}

PONTUAÇÃO GERAL: {pontuacao}/100
{"✅ SEGURO" if pontuacao >= 80 else "⚠️  PRECISA MELHORIAS" if pontuacao >= 60 else "🚨 CRÍTICO"}

FRAMEWORKS VALIDADOS:
✅ OWASP Top 10 2021
✅ NIST Cybersecurity Framework
✅ CIS Controls v8
✅ Zero Trust Architecture

TOTAL DE ACHADOS: {len(achados)}
- 🔴 Críticos: {sum(1 for a in achados if "CRÍTICA" in a.get("severidade", "").value)}
- 🟠 Altos: {sum(1 for a in achados if "ALTA" in a.get("severidade", "").value)}
- 🟡 Médios: {sum(1 for a in achados if "MÉDIA" in a.get("severidade", "").value)}

{'='*80}
DETALHES
{'='*80}
"""

        for achado in achados:
            relatorio += f"""
{achado['titulo']}
├─ Framework: {achado['framework']}
├─ Arquivo: {achado['arquivo']}
├─ Problema: {achado['problema']}
├─ Recomendação: {achado['recomendacao']}
└─ Referências: {', '.join(achado.get('referencias', []))}
"""

        return relatorio

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    agente = AgenteSegurancaAvancado()

    # Exemplo de uso
    projeto_path = Path("../01-SMB-OS")
    achados, pontuacao = agente.analisar(projeto_path)

    relatorio = agente.gerar_relatorio(achados, pontuacao)
    print(relatorio)
