import os, hashlib, hmac, secrets, re
from datetime import datetime, timedelta
from typing import Optional
from cryptography.fernet import Fernet
from jose import jwt, JWTError
from collections import defaultdict
from threading import Lock

JWT_ALGORITHM  = "HS256"
JWT_EXPIRE_HRS = 24

def _get_env(key):
    val = os.environ.get(key)
    if not val:
        raise EnvironmentError(f"Variavel '{key}' nao encontrada no .env")
    return val

def _cipher():
    import base64
    k = hashlib.sha256(_get_env("ENCRYPTION_KEY").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(k))

def encrypt(text: str) -> str:
    return _cipher().encrypt(text.encode()).decode() if text else ""

def decrypt(text: str) -> str:
    return _cipher().decrypt(text.encode()).decode() if text else ""

def hash_pii(value: str) -> str:
    """HMAC-SHA256 com salt — irreversivel, usado para busca."""
    salt = _get_env("ENCRYPTION_KEY")
    return hmac.new(salt.encode(), value.lower().strip().encode(), hashlib.sha256).hexdigest()

def hash_ip(ip: str) -> str:
    """Hash do IP para audit log — nunca guarda IP real."""
    salt = _get_env("ENCRYPTION_KEY") + "_ip"
    return hmac.new(salt.encode(), ip.encode(), hashlib.sha256).hexdigest()[:16]

def create_token(member_id: str, plan: str = "free") -> str:
    payload = {
        "sub": member_id, "plan": plan,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HRS),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, _get_env("JWT_SECRET"), algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _get_env("JWT_SECRET"), algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

def generate_referral_code() -> str:
    alpha = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alpha) for _ in range(8))

def generate_utm(member_id: str, deal_id: str) -> str:
    raw = f"{member_id}:{deal_id}:{secrets.token_hex(4)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]

def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)

_PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

def validate_phone(phone: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", phone.strip())
    if not cleaned.startswith("+"): cleaned = "+1" + cleaned
    if not _PHONE_RE.match(cleaned): raise ValueError("Telefone invalido.")
    return cleaned

def validate_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not _EMAIL_RE.match(cleaned): raise ValueError("Email invalido.")
    return cleaned

def sanitize(text: str, max_len: int = 100) -> str:
    if not text: return ""
    return re.sub(r"[\x00-\x1f\x7f]", "", text.strip())[:max_len]

_rate_store: dict = defaultdict(list)
_rate_lock = Lock()

def check_rate_limit(key: str, max_req: int, window_sec: int) -> bool:
    now = datetime.utcnow().timestamp()
    cutoff = now - window_sec
    with _rate_lock:
        _rate_store[key] = [t for t in _rate_store[key] if t > cutoff]
        if len(_rate_store[key]) >= max_req: return False
        _rate_store[key].append(now)
        return True

def generate_keys():
    import base64
    print(f"ENCRYPTION_KEY={base64.urlsafe_b64encode(os.urandom(32)).decode()}")
    print(f"JWT_SECRET={secrets.token_hex(32)}")
    print(f"API_SECRET_KEY={secrets.token_hex(32)}")

if __name__ == "__main__":
    generate_keys()
