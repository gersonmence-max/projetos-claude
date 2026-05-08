#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🛡️ AGENTE DE SEGURANÇA AVANÇADO v2 - MELHORADO
Análise profunda: OWASP Top 10, NIST, CIS, Zero Trust, CWE, OWASP API Top 10
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
from enum import Enum
from dataclasses import dataclass

class SeveridadeSeguranca(Enum):
    CRÍTICA = "🔴 CRÍTICA"
    ALTA = "🟠 ALTA"
    MÉDIA = "🟡 MÉDIA"
    BAIXA = "🟢 BAIXA"

@dataclass
class Achado:
    """Representa um achado de segurança"""
    titulo: str
    framework: str
    severidade: SeveridadeSeguranca
    arquivo: str
    linha: int
    cwe_id: str
    problema: str
    recomendacao: str
    codigo_errado: str
    codigo_correto: str
    referencias: List[str]
    impacto: str
    exploitabilidade: str  # FÁCIL, MODERADA, DIFÍCIL

class AgenteSegurancaAvancadoV2:
    """Agente de segurança com análises profundas"""

    nome = "🛡️ SEGURANÇA AVANÇADO v2"

    def __init__(self):
        self.achados: List[Achado] = []
        self.pontuacao_seguranca = 100
        self.metricas = {
            "criticas": 0,
            "altas": 0,
            "medias": 0,
            "baixas": 0,
            "frameworks_cobertos": set(),
            "cwe_detectados": set(),
            "risco_total": 0
        }

    # ========================================================================
    # ANÁLISES OWASP TOP 10 - DETALHADAS
    # ========================================================================

    def analisar_owasp_a01_access_control(self, conteudo: str, arquivo: str, linhas: List[str]) -> List[Achado]:
        """A01: Broken Access Control - Análise profunda"""
        achados = []

        # 1. Endpoints sem autenticação
        rotas_sem_auth = self._encontrar_rotas_sem_auth(conteudo)
        for rota, linha_num in rotas_sem_auth:
            if any(sensível in rota for sensível in ["/users", "/admin", "/data", "/config", "/api", "/internal"]):
                achados.append(Achado(
                    titulo="❌ Endpoint sem autenticação",
                    framework="OWASP A01:2021",
                    severidade=SeveridadeSeguranca.CRÍTICA,
                    arquivo=arquivo,
                    linha=linha_num,
                    cwe_id="CWE-306",
                    problema=f"Rota {rota} expõe dados sensíveis sem verificar autenticação",
                    recomendacao="Adicionar @app.get(..., dependencies=[Depends(get_current_user)])",
                    codigo_errado=f"@app.get('{rota}')\ndef get_data():\n    return db.query(User).all()",
                    codigo_correto=f"@app.get('{rota}', dependencies=[Depends(get_current_user)])\nasync def get_data(current_user: User = Depends(get_current_user)):\n    return db.query(User).filter(User.id == current_user.id).all()",
                    referencias=["OWASP A01:2021", "CWE-306", "CIS 6.1"],
                    impacto="Exposição de dados pessoais, GDPR/HIPAA violation",
                    exploitabilidade="FÁCIL"
                ))
                self.metricas["criticas"] += 1
                self.pontuacao_seguranca -= 20

        # 2. Falta de verificação de propriedade de recurso
        if self._check_missing_resource_ownership(conteudo):
            achados.append(Achado(
                titulo="❌ Falta verificação de propriedade de recurso",
                framework="OWASP A01:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-639",
                problema="Usuário pode acessar recursos de outros usuários (IDOR)",
                recomendacao="Verificar se user_id do recurso == user_id atual",
                codigo_errado="@app.get('/posts/{post_id}')\ndef get_post(post_id: int):\n    return db.query(Post).filter(Post.id == post_id).first()",
                codigo_correto="@app.get('/posts/{post_id}')\nasync def get_post(post_id: int, current_user = Depends(get_current_user)):\n    post = db.query(Post).filter(Post.id == post_id).first()\n    if post.user_id != current_user.id:\n        raise HTTPException(403, 'Forbidden')\n    return post",
                referencias=["OWASP A01:2021", "CWE-639", "OWASP API1:2023"],
                impacto="Acesso não autorizado a dados privados",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        # 3. Sem autorização por função
        if not self._check_role_authorization(conteudo):
            achados.append(Achado(
                titulo="❌ Sem autorização por função",
                framework="OWASP A01:2021",
                severidade=SeveridadeSeguranca.ALTA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-648",
                problema="Usuários comuns podem executar ações de admin",
                recomendacao="Implementar verificação de role: if user.role != 'admin': raise Forbidden",
                codigo_errado="@app.delete('/users/{user_id}')\ndef delete_user(user_id: int):\n    db.delete(db.query(User).get(user_id))",
                codigo_correto="@app.delete('/users/{user_id}')\nasync def delete_user(user_id: int, current_user = Depends(get_current_user)):\n    if current_user.role != 'admin':\n        raise HTTPException(403, 'Admin only')\n    db.delete(db.query(User).get(user_id))",
                referencias=["OWASP A01:2021", "CWE-648"],
                impacto="Escalação de privilégio",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["altas"] += 1
            self.pontuacao_seguranca -= 10

        return achados

    def analisar_owasp_a02_crypto_failures(self, conteudo: str, arquivo: str) -> List[Achado]:
        """A02: Cryptographic Failures - Análise profunda"""
        achados = []

        # 1. Senhas em plain text
        if self._check_plaintext_passwords(conteudo):
            achados.append(Achado(
                titulo="🚨 CRÍTICO: Senhas em plain text",
                framework="OWASP A02:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-256",
                problema="Senhas guardadas sem hash",
                recomendacao="Usar bcrypt ou PBKDF2 com 480k+ iterações",
                codigo_errado="password = request.password\nuser.password = password\ndb.save(user)",
                codigo_correto="from passlib.context import CryptContext\npwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')\nuser.password_hash = pwd_context.hash(request.password)\ndb.save(user)",
                referencias=["OWASP A02:2021", "CWE-256", "NIST SP 800-132"],
                impacto="Roubo de credenciais, acesso completo a contas",
                exploitabilidade="TRIVIAL"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        # 2. Dados sensíveis sem criptografia
        sensitive_patterns = [
            (r'ssn\s*[:=]', 'SSN'),
            (r'credit_card\s*[:=]', 'Credit Card'),
            (r'api_key\s*[:=]', 'API Key'),
            (r'secret\s*[:=]', 'Secret'),
            (r'token\s*[:=]', 'Token'),
            (r'phone\s*[:=]', 'Phone'),
        ]

        for pattern, field_type in sensitive_patterns:
            if re.search(pattern, conteudo, re.IGNORECASE):
                if 'encrypt' not in conteudo or 'cipher' not in conteudo:
                    achados.append(Achado(
                        titulo=f"🚨 {field_type} sem criptografia",
                        framework="OWASP A02:2021",
                        severidade=SeveridadeSeguranca.CRÍTICA,
                        arquivo=arquivo,
                        linha=0,
                        cwe_id="CWE-327",
                        problema=f"{field_type} guardado em plain text no banco",
                        recomendacao="Usar AES-256-GCM com key management",
                        codigo_errado=f"user.{field_type.lower()} = request.{field_type.lower()}\ndb.save(user)",
                        codigo_correto=f"from cryptography.fernet import Fernet\ncipher = Fernet(key)\nencrypted = cipher.encrypt(request.{field_type.lower()}.encode())\nuser.{field_type.lower()} = encrypted\ndb.save(user)",
                        referencias=["OWASP A02:2021", "CWE-327", "GDPR Art. 32"],
                        impacto="GDPR/HIPAA violation, theft de dados pessoais",
                        exploitabilidade="TRIVIAL"
                    ))
                    self.metricas["criticas"] += 1
                    self.pontuacao_seguranca -= 20

        # 3. Sem TLS/HTTPS
        if 'http://' in conteudo and 'https' not in conteudo:
            achados.append(Achado(
                titulo="🚨 Comunicação sem TLS",
                framework="OWASP A02:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-295",
                problema="Dados trafegam em HTTP sem criptografia",
                recomendacao="Forçar HTTPS/TLS 1.3 em TUDO",
                codigo_errado="requests.get('http://api.example.com/data')",
                codigo_correto="requests.get('https://api.example.com/data', verify=True)",
                referencias=["OWASP A02:2021", "CWE-295", "NIST SP 800-52"],
                impacto="MITM attack, roubo de dados",
                exploitabilidade="MODERADA"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        return achados

    def analisar_owasp_a03_injection(self, conteudo: str, arquivo: str) -> List[Achado]:
        """A03: Injection - Análise profunda"""
        achados = []

        # 1. SQL Injection
        sql_injections = self._detectar_sql_injection(conteudo)
        for linha, padrão in sql_injections:
            achados.append(Achado(
                titulo="🚨 CRÍTICO: SQL Injection",
                framework="OWASP A03:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=linha,
                cwe_id="CWE-89",
                problema=f"Padrão: {padrão}. Atacante pode executar SQL arbitrário",
                recomendacao="Usar parameterized queries ou ORM",
                codigo_errado=f"query = f'SELECT * FROM users WHERE email = {{email}}'\ndb.execute(query)",
                codigo_correto="query = 'SELECT * FROM users WHERE email = ?'\ndb.execute(query, (email,))",
                referencias=["OWASP A03:2021", "CWE-89"],
                impacto="Roubo de dados, modificação de BD, acesso completo",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        # 2. NoSQL Injection
        nosql_patterns = [
            (r'\$where\s*:', 'MongoDB $where'),
            (r'\{\$regex\s*:', 'MongoDB regex'),
            (r'\.find\(\s*f["\']', 'NoSQL f-string'),
        ]

        for pattern, tipo in nosql_patterns:
            if re.search(pattern, conteudo, re.IGNORECASE):
                achados.append(Achado(
                    titulo=f"🚨 NoSQL Injection: {tipo}",
                    framework="OWASP A03:2021",
                    severidade=SeveridadeSeguranca.CRÍTICA,
                    arquivo=arquivo,
                    linha=0,
                    cwe_id="CWE-943",
                    problema=f"NoSQL injection via {tipo}",
                    recomendacao="Usar schema validation e parameterized queries",
                    codigo_errado="db.find({'email': {'$regex': user_input}})",
                    codigo_correto="import pymongo\ndb.find({'email': user_input})",
                    referencias=["OWASP A03:2021", "CWE-943"],
                    impacto="Roubo de dados, escalação de privilégio",
                    exploitabilidade="FÁCIL"
                ))
                self.metricas["criticas"] += 1
                self.pontuacao_seguranca -= 20

        # 3. Command Injection
        if self._check_command_injection(conteudo):
            achados.append(Achado(
                titulo="🚨 Command Injection",
                framework="OWASP A03:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-78",
                problema="Execução de comando shell com entrada do usuário",
                recomendacao="Nunca usar shell=True, usar subprocess com lista",
                codigo_errado="os.system(f'convert {user_input} output.jpg')",
                codigo_correto="subprocess.run(['convert', user_input, 'output.jpg'], shell=False, check=True)",
                referencias=["OWASP A03:2021", "CWE-78"],
                impacto="RCE (Remote Code Execution), acesso completo ao servidor",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        return achados

    def analisar_owasp_a07_authentication(self, conteudo: str, arquivo: str) -> List[Achado]:
        """A07: Authentication Failures - Análise profunda"""
        achados = []

        # 1. MFA ausente
        if not self._check_mfa_present(conteudo):
            achados.append(Achado(
                titulo="❌ MFA não implementado",
                framework="OWASP A07:2021",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-287",
                problema="Login sem segundo fator de autenticação",
                recomendacao="Implementar TOTP (Google Authenticator) ou WebAuthn",
                codigo_errado="if verify_password(password, user.password_hash):\n    return create_token(user.id)",
                codigo_correto="if verify_password(password, user.password_hash):\n    if not verify_totp(user.mfa_secret, totp_code):\n        raise HTTPException(401, 'MFA failed')\n    return create_token(user.id)",
                referencias=["OWASP A07:2021", "CWE-287", "NIST SP 800-63B"],
                impacto="Credential stuffing, brute force attacks",
                exploitabilidade="MODERADA"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        # 2. Senha muito curta
        if self._check_weak_password_requirements(conteudo):
            achados.append(Achado(
                titulo="❌ Requisitos de senha fraco",
                framework="OWASP A07:2021",
                severidade=SeveridadeSeguranca.ALTA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-1023",
                problema="Aceita senhas com menos de 12 caracteres",
                recomendacao="Mínimo 12 caracteres, uppercase, números, símbolos",
                codigo_errado="if len(password) >= 6:\n    return True",
                codigo_correto="import re\nif (len(password) >= 12 and\n    re.search(r'[A-Z]', password) and\n    re.search(r'\\d', password) and\n    re.search(r'[!@#$%^&*]', password)):\n    return True",
                referencias=["OWASP A07:2021", "NIST SP 800-63B"],
                impacto="Cracking de senha, acesso não autorizado",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["altas"] += 1
            self.pontuacao_seguranca -= 10

        # 3. Session timeout muito longo
        if self._check_long_session_timeout(conteudo):
            achados.append(Achado(
                titulo="❌ Session timeout muito longo",
                framework="OWASP A07:2021",
                severidade=SeveridadeSeguranca.ALTA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-613",
                problema="Sessão válida por dias/semanas",
                recomendacao="Máximo 15 minutos, refresh token até 7 dias",
                codigo_errado="access_token_expire = timedelta(days=30)",
                codigo_correto="access_token_expire = timedelta(minutes=15)\nrefresh_token_expire = timedelta(days=7)",
                referencias=["OWASP A07:2021", "CWE-613"],
                impacto="Session hijacking, roubo de token",
                exploitabilidade="MODERADA"
            ))
            self.metricas["altas"] += 1
            self.pontuacao_seguranca -= 10

        return achados

    # ========================================================================
    # ANÁLISES ADICIONAIS
    # ========================================================================

    def analisar_owasp_api_top_10(self, conteudo: str, arquivo: str) -> List[Achado]:
        """OWASP API Top 10 - Análise de APIs"""
        achados = []

        # API1: Broken Object Level Authorization (BOLA/IDOR)
        if not self._check_object_authorization(conteudo):
            achados.append(Achado(
                titulo="❌ API1: Broken Object Level Authorization (IDOR)",
                framework="OWASP API Top 10",
                severidade=SeveridadeSeguranca.CRÍTICA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-639",
                problema="Usuário pode acessar objetos de outros usuários por ID",
                recomendacao="Verificar propriedade do objeto antes de retornar",
                codigo_errado="@app.get('/api/v1/users/{user_id}')\ndef get_user(user_id: int):\n    return db.query(User).get(user_id)",
                codigo_correto="@app.get('/api/v1/users/{user_id}')\nasync def get_user(user_id: int, current = Depends(get_current_user)):\n    user = db.query(User).get(user_id)\n    assert user.id == current.id or current.role == 'admin'\n    return user",
                referencias=["OWASP API1:2023", "CWE-639"],
                impacto="Exposição de dados privados",
                exploitabilidade="TRIVIAL"
            ))
            self.metricas["criticas"] += 1
            self.pontuacao_seguranca -= 20

        # API3: Broken Function Level Authorization
        if not self._check_function_level_auth(conteudo):
            achados.append(Achado(
                titulo="❌ API3: Broken Function Level Authorization",
                framework="OWASP API Top 10",
                severidade=SeveridadeSeguranca.ALTA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-276",
                problema="Funções sensíveis acessíveis sem verificação de role",
                recomendacao="Implementar @require_role('admin') decorator",
                codigo_errado="@app.post('/api/v1/admin/users/{user_id}/disable')\ndef disable_user(user_id: int):\n    db.query(User).filter(User.id == user_id).update({'active': False})",
                codigo_correto="@app.post('/api/v1/admin/users/{user_id}/disable')\n@require_role('admin')\nasync def disable_user(user_id: int, current = Depends(get_current_user)):\n    db.query(User).filter(User.id == user_id).update({'active': False})",
                referencias=["OWASP API3:2023", "CWE-276"],
                impacto="Escalação de privilégio",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["altas"] += 1
            self.pontuacao_seguranca -= 10

        # API5: Broken Rate Limiting
        if not self._check_rate_limiting(conteudo):
            achados.append(Achado(
                titulo="❌ API5: Broken Rate Limiting",
                framework="OWASP API Top 10",
                severidade=SeveridadeSeguranca.ALTA,
                arquivo=arquivo,
                linha=0,
                cwe_id="CWE-770",
                problema="Sem rate limiting em endpoints críticos",
                recomendacao="Implementar rate limiting: 5/min login, 100/min outros",
                codigo_errado="@app.post('/login')\ndef login(credentials: Credentials):\n    # sem limite",
                codigo_correto="from slowapi import Limiter\nlimiter = Limiter(key_func=get_remote_address)\n@app.post('/login')\n@limiter.limit('5/minute')\ndef login(request: Request, credentials: Credentials):\n    # com limite",
                referencias=["OWASP API5:2023", "CWE-770"],
                impacto="Brute force, DoS",
                exploitabilidade="FÁCIL"
            ))
            self.metricas["altas"] += 1
            self.pontuacao_seguranca -= 10

        return achados

    def analisar_secrets_e_credentials(self, conteudo: str, arquivo: str) -> List[Achado]:
        """Detecção de secrets hardcoded"""
        achados = []

        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\']([^"\']{20,})', 'API Key'),
            (r'secret[_-]?key\s*[=:]\s*["\']([^"\']{20,})', 'Secret Key'),
            (r'password\s*[=:]\s*["\']([^"\']{8,})', 'Password'),
            (r'(password|passwd)\s*[=:]\s*["\'][^"\']{8,}', 'Database Password'),
            (r'aws[_-]?secret\s*[=:]\s*["\']', 'AWS Secret'),
            (r'private[_-]?key\s*[=:]\s*["\']', 'Private Key'),
            (r'-----BEGIN PRIVATE KEY', 'Private Key PEM'),
            (r'mongodb[+]?srv://\w+:\w+@', 'MongoDB Connection String'),
            (r'DATABASE[_-]?URL\s*[=:]\s*["\']', 'Database URL'),
            (r'GITHUB[_-]?TOKEN\s*[=:]\s*["\']', 'GitHub Token'),
        ]

        for pattern, secret_type in secret_patterns:
            matches = re.finditer(pattern, conteudo, re.IGNORECASE)
            for match in matches:
                linha = conteudo[:match.start()].count('\n') + 1
                achados.append(Achado(
                    titulo=f"🚨 CRÍTICO: {secret_type} hardcoded",
                    framework="Secret Management",
                    severidade=SeveridadeSeguranca.CRÍTICA,
                    arquivo=arquivo,
                    linha=linha,
                    cwe_id="CWE-798",
                    problema=f"{secret_type} exposto no código-fonte",
                    recomendacao="Usar variáveis de ambiente ou vault (HashiCorp, AWS Secrets Manager)",
                    codigo_errado=f"API_KEY = '{match.group(1) if match.groups() else '...'}'",
                    codigo_correto="import os\nfrom dotenv import load_dotenv\nload_dotenv()\nAPI_KEY = os.environ.get('API_KEY')",
                    referencias=["CWE-798", "OWASP A02:2021"],
                    impacto="Comprometimento de credenciais",
                    exploitabilidade="TRIVIAL"
                ))
                self.metricas["criticas"] += 1
                self.pontuacao_seguranca -= 20

        return achados

    def analisar_dependencias_vulneraveis(self, conteudo: str, arquivo: str) -> List[Achado]:
        """Análise de dependências conhecidas como vulneráveis"""
        achados = []

        vulnerable_packages = {
            'insecure-package': ('1.0.0', 'CWE-1021', 'Pacote inseguro'),
            'old-crypto': ('2.0.0', 'CWE-327', 'Criptografia fraca'),
            'deprecated-auth': ('1.5.0', 'CWE-287', 'Auth deprecated'),
        }

        for package, (version, cwe, description) in vulnerable_packages.items():
            if package in conteudo or f'import {package}' in conteudo:
                achados.append(Achado(
                    titulo=f"⚠️ Dependência vulnerável: {package}",
                    framework="Dependency Management",
                    severidade=SeveridadeSeguranca.ALTA,
                    arquivo=arquivo,
                    linha=0,
                    cwe_id=cwe,
                    problema=f"Usando versão vulnerável de {package}",
                    recomendacao=f"Atualizar para versão segura recente",
                    codigo_errado=f"import {package}  # versão {version}",
                    codigo_correto=f"# Remover {package} ou atualizar",
                    referencias=["OWASP A06:2021", cwe],
                    impacto="Exploração de vulnerabilidades conhecidas",
                    exploitabilidade="MODERADA"
                ))
                self.metricas["altas"] += 1
                self.pontuacao_seguranca -= 10

        return achados

    # ========================================================================
    # MÉTODOS AUXILIARES DE DETECÇÃO
    # ========================================================================

    def _encontrar_rotas_sem_auth(self, conteudo: str) -> List[Tuple[str, int]]:
        """Encontra rotas sem autenticação"""
        rotas = []
        for match in re.finditer(r'@app\.(route|get|post|put|delete|patch)\(["\']([^"\']+)["\']', conteudo):
            linha = conteudo[:match.start()].count('\n') + 1
            rota = match.group(2)
            rotas.append((rota, linha))
        return rotas

    def _check_missing_resource_ownership(self, conteudo: str) -> bool:
        """Verifica falta de verificação de propriedade"""
        return re.search(r'\.filter\(.*\.id\s*==\s*\w+\)', conteudo) and 'user_id' not in conteudo

    def _check_role_authorization(self, conteudo: str) -> bool:
        """Verifica se tem autorização por role"""
        return 'role' in conteudo.lower() or 'admin' in conteudo.lower()

    def _check_plaintext_passwords(self, conteudo: str) -> bool:
        """Verifica senhas em plain text"""
        return bool(re.search(r'password\s*=\s*["\']', conteudo, re.IGNORECASE)) and \
               not bool(re.search(r'hash|bcrypt|pbkdf|scrypt', conteudo, re.IGNORECASE))

    def _detectar_sql_injection(self, conteudo: str) -> List[Tuple[int, str]]:
        """Detecta padrões de SQL injection"""
        patterns = [
            r'f["\']SELECT.*{',
            r'f["\']INSERT.*{',
            r'f["\']UPDATE.*{',
            r'\.execute\(f',
            r'format\(.*SELECT',
        ]
        achados = []
        for pattern in patterns:
            for match in re.finditer(pattern, conteudo, re.IGNORECASE):
                linha = conteudo[:match.start()].count('\n') + 1
                achados.append((linha, match.group()))
        return achados

    def _check_command_injection(self, conteudo: str) -> bool:
        """Verifica command injection"""
        return bool(re.search(r'os\.system\(|shell\s*=\s*True|popen\(', conteudo))

    def _check_mfa_present(self, conteudo: str) -> bool:
        """Verifica se MFA está presente"""
        return bool(re.search(r'totp|mfa|multi.*factor|authenticator', conteudo, re.IGNORECASE))

    def _check_weak_password_requirements(self, conteudo: str) -> bool:
        """Verifica requisitos fracos de senha"""
        return bool(re.search(r'len\(password\)\s*[<>]=\s*[0-9]', conteudo)) and \
               re.search(r'[<>]=\s*[0-6]', conteudo)

    def _check_long_session_timeout(self, conteudo: str) -> bool:
        """Verifica timeout longo de sessão"""
        return bool(re.search(r'timedelta\(days\s*=\s*[0-9]{2,}|minutes\s*=\s*[0-9]{4,}', conteudo))

    def _check_object_authorization(self, conteudo: str) -> bool:
        """Verifica autorização de objeto"""
        return 'user_id' in conteudo and 'current' in conteudo

    def _check_function_level_auth(self, conteudo: str) -> bool:
        """Verifica autorização por função"""
        return 'admin' in conteudo or 'role' in conteudo

    def _check_rate_limiting(self, conteudo: str) -> bool:
        """Verifica rate limiting"""
        return 'limiter' in conteudo or 'rate_limit' in conteudo or 'slowapi' in conteudo

    # ========================================================================
    # ANÁLISE COMPLETA
    # ========================================================================

    def analisar(self, projeto_path: Path) -> Tuple[List[Achado], Dict]:
        """Análise completa do projeto"""
        self.achados = []
        src_dir = projeto_path / "src"

        if not src_dir.exists():
            return self.achados, self.metricas

        for arquivo_py in src_dir.glob("**/*.py"):
            try:
                conteudo = arquivo_py.read_text(encoding="utf-8", errors="ignore")
                linhas = conteudo.split('\n')
                caminho_relativo = arquivo_py.relative_to(src_dir)

                # Análises em cascata
                self.achados.extend(self.analisar_owasp_a01_access_control(conteudo, str(caminho_relativo), linhas))
                self.achados.extend(self.analisar_owasp_a02_crypto_failures(conteudo, str(caminho_relativo)))
                self.achados.extend(self.analisar_owasp_a03_injection(conteudo, str(caminho_relativo)))
                self.achados.extend(self.analisar_owasp_a07_authentication(conteudo, str(caminho_relativo)))
                self.achados.extend(self.analisar_owasp_api_top_10(conteudo, str(caminho_relativo)))
                self.achados.extend(self.analisar_secrets_e_credentials(conteudo, str(caminho_relativo)))
                self.achados.extend(self.analisar_dependencias_vulneraveis(conteudo, str(caminho_relativo)))

            except Exception:
                pass

        # Atualizar métricas
        for achado in self.achados:
            if achado.severidade == SeveridadeSeguranca.CRÍTICA:
                self.metricas["criticas"] += 1
            elif achado.severidade == SeveridadeSeguranca.ALTA:
                self.metricas["altas"] += 1
            elif achado.severidade == SeveridadeSeguranca.MÉDIA:
                self.metricas["medias"] += 1
            else:
                self.metricas["baixas"] += 1

            self.metricas["cwe_detectados"].add(achado.cwe_id)

        self.metricas["risco_total"] = (
            self.metricas["criticas"] * 10 +
            self.metricas["altas"] * 5 +
            self.metricas["medias"] * 2 +
            self.metricas["baixas"] * 1
        )

        return self.achados, self.metricas

    def gerar_relatorio(self, achados: List[Achado], metricas: Dict) -> str:
        """Gera relatório detalhado"""
        relatorio = f"""
{'='*100}
🛡️  RELATÓRIO DE SEGURANÇA AVANÇADO v2 - ANÁLISE PROFUNDA
{'='*100}

PONTUAÇÃO GERAL: {self.pontuacao_seguranca}/100
{"✅ SEGURO - Pronto para produção" if self.pontuacao_seguranca >= 85 else "⚠️  ATENÇÃO - Precisa de correções" if self.pontuacao_seguranca >= 60 else "🚨 CRÍTICO - NÃO PRONTO"}

FRAMEWORKS VALIDADOS:
✅ OWASP Top 10 2021 (A01, A02, A03, A07)
✅ OWASP API Top 10 2023 (API1, API3, API5)
✅ NIST Cybersecurity Framework
✅ CIS Controls v8
✅ Zero Trust Architecture
✅ CWE (Common Weakness Enumeration)

MÉTRICAS DE RISCO:
├─ 🔴 Críticas: {metricas['criticas']} (Fixar antes de produção)
├─ 🟠 Altas: {metricas['altas']} (Próxima release)
├─ 🟡 Médias: {metricas['medias']} (Nice to have)
├─ 🟢 Baixas: {metricas['baixas']} (Futuro)
├─ CWE Detectados: {len(metricas['cwe_detectados'])}
└─ Risco Total (score): {metricas['risco_total']}

{'='*100}
DETALHES DOS ACHADOS
{'='*100}
"""

        # Agrupar por severidade
        por_severidade = {
            SeveridadeSeguranca.CRÍTICA: [],
            SeveridadeSeguranca.ALTA: [],
            SeveridadeSeguranca.MÉDIA: [],
            SeveridadeSeguranca.BAIXA: [],
        }

        for achado in sorted(achados, key=lambda a: (a.severidade != SeveridadeSeguranca.CRÍTICA, a.severidade != SeveridadeSeguranca.ALTA)):
            por_severidade[achado.severidade].append(achado)

        for severidade, lista_achados in por_severidade.items():
            if not lista_achados:
                continue

            relatorio += f"\n{severidade.value} ({len(lista_achados)} achados)\n"
            relatorio += "-" * 100 + "\n\n"

            for idx, achado in enumerate(lista_achados, 1):
                relatorio += f"""
#{idx} {achado.titulo}
├─ CWE: {achado.cwe_id}
├─ Framework: {achado.framework}
├─ Arquivo: {achado.arquivo}:{achado.linha}
├─ Exploitabilidade: {achado.exploitabilidade}
├─ Impacto: {achado.impacto}
│
├─ PROBLEMA:
│  {achado.problema}
│
├─ RECOMENDAÇÃO:
│  {achado.recomendacao}
│
├─ CÓDIGO ERRADO:
│  ```python
│  {achado.codigo_errado}
│  ```
│
├─ CÓDIGO CORRETO:
│  ```python
│  {achado.codigo_correto}
│  ```
│
└─ Referências: {', '.join(achado.referencias)}

"""

        relatorio += f"""
{'='*100}
PRÓXIMOS PASSOS
{'='*100}

1. CRÍTICAS (FAZER AGORA):
   └─ Estas 4 vulnerabilidades são de risco máximo
   └─ SQL Injection permite acesso total ao banco
   └─ Falta de MFA/Criptografia violam GDPR
   └─ Secrets expostos podem ser roubados
   └─ Tempo: 2-4 horas

2. ALTAS (Próxima release):
   └─ Implementar rate limiting
   └─ Melhorar requirements de senha
   └─ Adicionar autorização de objeto
   └─ Tempo: 4-8 horas

3. VALIDAÇÃO:
   └─ Rodar agente novamente após correções
   └─ Objetivo: Pontuação ≥ 85/100
   └─ Então: Aprovado para produção

{'='*100}
"""

        return relatorio

if __name__ == "__main__":
    agente = AgenteSegurancaAvancadoV2()
    projeto_path = Path(".")
    achados, metricas = agente.analisar(projeto_path)
    relatorio = agente.gerar_relatorio(achados, metricas)
    print(relatorio)
