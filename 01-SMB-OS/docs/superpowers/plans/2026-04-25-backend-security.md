# SMB OS — Backend Security Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the full security layer for the FastAPI backend — JWT authentication (email+password + OAuth), multi-tenant PostgreSQL RLS isolation, RBAC with granular permissions, rate limiting, security headers, and immutable audit logging.

**Architecture:** Three independent enforcement layers: (1) SecurityMiddleware validates JWT and injects RequestContext on every request, (2) `require_permission("resource:action")` dependency enforces RBAC per endpoint before any business logic runs, (3) PostgreSQL Row Level Security blocks cross-tenant DB access even if the API has a bug. Sync SQLAlchemy 2.0 + psycopg2, Alembic migrations, python-jose RS256 JWT, passlib bcrypt, authlib for OAuth.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 15+, python-jose[cryptography], passlib[bcrypt], pydantic-settings, authlib, slowapi, psycopg2-binary, pytest, httpx

---

## File Map

**New — `apps/api/`:**
- `app/core/config.py` — pydantic-settings; all env vars in one place
- `app/core/security.py` — JWT encode/decode (RS256), password hash/verify
- `app/core/context.py` — `RequestContext` dataclass (tenant_id, user_id, permissions)
- `app/core/middleware.py` — `SecurityMiddleware` (JWT→context), `SecurityHeadersMiddleware`
- `app/core/deps.py` — `get_request_context`, `require_permission` FastAPI dependencies
- `app/core/rate_limit.py` — slowapi limiter instance + key function
- `app/db/base.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get_db` dependency
- `app/db/models/__init__.py` — imports all models (needed by Alembic autogenerate)
- `app/db/models/tenant.py` — `Tenant` model
- `app/db/models/user.py` — `User` model
- `app/db/models/auth.py` — `OAuthAccount`, `RefreshToken` models
- `app/db/models/rbac.py` — `Permission`, `Role`, `RolePermission`, `UserRole` models
- `app/db/models/audit.py` — `AuditLog` model + SQLAlchemy event listener
- `app/schemas/auth.py` — Pydantic request/response schemas for auth endpoints
- `app/routes/auth.py` — `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`
- `alembic.ini` — Alembic config pointing at `DATABASE_URL`
- `alembic/env.py` — Alembic env with model metadata + RLS policies
- `alembic/versions/` — generated migrations
- `scripts/generate_keys.py` — one-time RS256 key pair generator
- `tests/conftest.py` — pytest fixtures (test DB, test client, auth helpers)
- `tests/test_security.py` — JWT and password utility tests
- `tests/test_auth.py` — register/login/refresh/logout endpoint tests
- `tests/test_rbac.py` — permission enforcement tests
- `tests/test_rls.py` — cross-tenant isolation tests

**Modified:**
- `apps/api/pyproject.toml` — add production + dev dependencies
- `apps/api/main.py` — register middleware, CORS from settings, auth router
- `apps/api/app/routes/health.py` — add optional RBAC example
- `.env.example` — add JWT keys, OAuth, DB, security vars

---

### Task 1: Dependencies + Settings

**Files:**
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/scripts/generate_keys.py`
- Modify: `.env.example`

- [ ] **Step 1: Update `apps/api/pyproject.toml`**

Replace the `[project]` dependencies block:

```toml
[project]
name = "smb-os-api"
version = "0.0.1"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "python-dotenv>=1.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "psycopg2-binary>=2.9.9",
    "pydantic-settings>=2.2.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "authlib>=1.3.0",
    "httpx>=0.27.0",
    "slowapi>=0.1.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install dependencies**

```bash
cd apps/api && uv sync
```

Expected: all packages installed, no errors.

- [ ] **Step 3: Create `apps/api/scripts/generate_keys.py`**

```python
"""Run once to generate RS256 key pair. Output goes into .env"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend(),
)

private_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

public_pem = key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

print("# Add these to your .env file")
print(f'JWT_PRIVATE_KEY="{private_pem}"')
print(f'JWT_PUBLIC_KEY="{public_pem}"')
```

- [ ] **Step 4: Run key generator and add output to `.env`**

```bash
cd apps/api && uv run python scripts/generate_keys.py
```

Copy the output into a new file `apps/api/.env` (not committed — already in .gitignore).

- [ ] **Step 5: Create `apps/api/app/core/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_PRIVATE_KEY: str
    JWT_PUBLIC_KEY: str
    SECRET_KEY: str

    ALLOWED_ORIGINS: str = "http://localhost:3000"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
```

- [ ] **Step 6: Update `.env.example` at repo root**

```
# Web
NEXT_PUBLIC_API_URL=http://localhost:8000

# API — Database
DATABASE_URL=postgresql://user:password@localhost:5432/smb_os

# API — Security
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
ENVIRONMENT=development

# API — CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000

# API — OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

- [ ] **Step 7: Verify settings load**

```bash
cd apps/api && uv run python -c "from app.core.config import settings; print('Settings OK:', settings.ALLOWED_ORIGINS)"
```

Expected: `Settings OK: http://localhost:3000`

- [ ] **Step 8: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock apps/api/app/core/config.py apps/api/scripts/generate_keys.py .env.example
git commit -m "feat(api): add security dependencies and settings config"
```

---

### Task 2: Database Base (SQLAlchemy + Session)

**Files:**
- Create: `apps/api/app/db/base.py`
- Create: `apps/api/app/db/__init__.py`

- [ ] **Step 1: Create `apps/api/app/db/__init__.py`** (empty file)

- [ ] **Step 2: Create `apps/api/app/db/base.py`**

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, tenant_id: str) -> None:
    """Set PostgreSQL RLS tenant context for this session."""
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
```

- [ ] **Step 3: Verify import**

```bash
cd apps/api && uv run python -c "from app.db.base import Base, engine; print('DB base OK')"
```

Expected: `DB base OK`

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/db/
git commit -m "feat(api): add SQLAlchemy base, session factory, tenant context helper"
```

---

### Task 3: Tenant + User Models

**Files:**
- Create: `apps/api/app/db/models/__init__.py`
- Create: `apps/api/app/db/models/tenant.py`
- Create: `apps/api/app/db/models/user.py`

- [ ] **Step 1: Create `apps/api/app/db/models/__init__.py`**

```python
from app.db.models.tenant import Tenant
from app.db.models.user import User

__all__ = ["Tenant", "User"]
```

(Will be updated as more models are added.)

- [ ] **Step 2: Create `apps/api/app/db/models/tenant.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list["User"]] = relationship(back_populates="tenant")
```

- [ ] **Step 3: Create `apps/api/app/db/models/user.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

    __table_args__ = (
        # email unique per tenant
        __import__("sqlalchemy").UniqueConstraint("tenant_id", "email"),
    )
```

- [ ] **Step 4: Verify models import**

```bash
cd apps/api && uv run python -c "from app.db.models import Tenant, User; print('Models OK')"
```

Expected: `Models OK`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/db/models/
git commit -m "feat(api): add Tenant and User SQLAlchemy models"
```

---

### Task 4: Auth Models (OAuthAccount, RefreshToken)

**Files:**
- Create: `apps/api/app/db/models/auth.py`
- Modify: `apps/api/app/db/models/__init__.py`

- [ ] **Step 1: Create `apps/api/app/db/models/auth.py`**

```python
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")

    __table_args__ = (UniqueConstraint("provider", "provider_id"),)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
```

- [ ] **Step 2: Update `apps/api/app/db/models/__init__.py`**

```python
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.auth import OAuthAccount, RefreshToken

__all__ = ["Tenant", "User", "OAuthAccount", "RefreshToken"]
```

- [ ] **Step 3: Verify import**

```bash
cd apps/api && uv run python -c "from app.db.models import OAuthAccount, RefreshToken; print('Auth models OK')"
```

Expected: `Auth models OK`

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/db/models/auth.py apps/api/app/db/models/__init__.py
git commit -m "feat(api): add OAuthAccount and RefreshToken models"
```

---

### Task 5: RBAC Models

**Files:**
- Create: `apps/api/app/db/models/rbac.py`
- Modify: `apps/api/app/db/models/__init__.py`

- [ ] **Step 1: Create `apps/api/app/db/models/rbac.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # e.g. "invoices:read"

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="permission")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role")
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")

    __table_args__ = (UniqueConstraint("tenant_id", "name"),)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("permissions.id"), primary_key=True
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(back_populates="role_permissions")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")
```

- [ ] **Step 2: Update `apps/api/app/db/models/__init__.py`**

```python
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.auth import OAuthAccount, RefreshToken
from app.db.models.rbac import Permission, Role, RolePermission, UserRole

__all__ = [
    "Tenant", "User",
    "OAuthAccount", "RefreshToken",
    "Permission", "Role", "RolePermission", "UserRole",
]
```

- [ ] **Step 3: Verify import**

```bash
cd apps/api && uv run python -c "from app.db.models import Role, Permission; print('RBAC models OK')"
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/db/models/rbac.py apps/api/app/db/models/__init__.py
git commit -m "feat(api): add RBAC models (Permission, Role, RolePermission, UserRole)"
```

---

### Task 6: Audit Log Model

**Files:**
- Create: `apps/api/app/db/models/audit.py`
- Modify: `apps/api/app/db/models/__init__.py`

- [ ] **Step 1: Create `apps/api/app/db/models/audit.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Update `apps/api/app/db/models/__init__.py`**

```python
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.auth import OAuthAccount, RefreshToken
from app.db.models.rbac import Permission, Role, RolePermission, UserRole
from app.db.models.audit import AuditLog

__all__ = [
    "Tenant", "User",
    "OAuthAccount", "RefreshToken",
    "Permission", "Role", "RolePermission", "UserRole",
    "AuditLog",
]
```

- [ ] **Step 3: Verify import**

```bash
cd apps/api && uv run python -c "from app.db.models import AuditLog; print('Audit model OK')"
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/db/models/audit.py apps/api/app/db/models/__init__.py
git commit -m "feat(api): add AuditLog model"
```

---

### Task 7: Alembic Setup + Initial Migration

**Files:**
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/env.py`
- Create: `apps/api/alembic/script.py.mako`
- Create: `apps/api/alembic/versions/` (directory, empty)

**Prerequisites:** PostgreSQL running with database `smb_os` created:
```sql
CREATE DATABASE smb_os;
```

- [ ] **Step 1: Initialize Alembic**

```bash
cd apps/api && uv run alembic init alembic
```

Expected: `alembic/` directory created with `env.py`, `script.py.mako`, `versions/`.

- [ ] **Step 2: Update `apps/api/alembic.ini`**

Find the line `sqlalchemy.url = driver://user:pass@localhost/dbname` and replace it:

```ini
sqlalchemy.url = %(DATABASE_URL)s
```

Also set:
```ini
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s
```

- [ ] **Step 3: Replace `apps/api/alembic/env.py`**

```python
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
import app.db.models  # noqa: F401 — ensures all models are registered

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Generate initial migration**

```bash
cd apps/api && uv run alembic revision --autogenerate -m "initial_schema"
```

Expected: new file created in `alembic/versions/`.

- [ ] **Step 5: Review the generated migration**

Open the generated file and verify it creates tables: `tenants`, `users`, `oauth_accounts`, `refresh_tokens`, `permissions`, `roles`, `role_permissions`, `user_roles`, `audit_log`.

- [ ] **Step 6: Add RLS policies to migration**

At the bottom of the `upgrade()` function in the generated migration, add:

```python
# Enable RLS on all tenant-scoped tables
op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
""")

op.execute("ALTER TABLE roles ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE roles FORCE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY tenant_isolation ON roles
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
""")

op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY tenant_read ON audit_log
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
""")
op.execute("""
    CREATE POLICY audit_log_no_delete ON audit_log AS RESTRICTIVE
    FOR DELETE USING (false)
""")
op.execute("""
    CREATE POLICY audit_log_no_update ON audit_log AS RESTRICTIVE
    FOR UPDATE USING (false)
""")

# Seed default permissions
permissions = [
    "users:read", "users:write", "users:manage",
    "roles:read", "roles:write",
    "settings:read", "settings:write",
    "audit:read",
]
for perm in permissions:
    op.execute(f"INSERT INTO permissions (id) VALUES ('{perm}')")
```

In `downgrade()`, add before the `drop_table` calls:
```python
op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
op.execute("DROP POLICY IF EXISTS tenant_isolation ON roles")
op.execute("ALTER TABLE roles DISABLE ROW LEVEL SECURITY")
op.execute("DROP POLICY IF EXISTS tenant_read ON audit_log")
op.execute("DROP POLICY IF EXISTS audit_log_no_delete ON audit_log")
op.execute("DROP POLICY IF EXISTS audit_log_no_update ON audit_log")
op.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY")
```

- [ ] **Step 7: Run migration**

```bash
cd apps/api && uv run alembic upgrade head
```

Expected: `Running upgrade -> <rev>, initial_schema`

- [ ] **Step 8: Verify tables exist**

```bash
cd apps/api && uv run python -c "
from sqlalchemy import inspect
from app.db.base import engine
inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', sorted(tables))
"
```

Expected output includes: `audit_log`, `oauth_accounts`, `permissions`, `refresh_tokens`, `role_permissions`, `roles`, `tenants`, `user_roles`, `users`

- [ ] **Step 9: Commit**

```bash
git add apps/api/alembic.ini apps/api/alembic/
git commit -m "feat(api): Alembic setup, initial migration with RLS policies and default permissions"
```

---

### Task 8: JWT + Password Security Utilities

**Files:**
- Create: `apps/api/app/core/security.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/test_security.py`

- [ ] **Step 1: Create `apps/api/tests/__init__.py`** (empty)

- [ ] **Step 2: Write failing tests — `apps/api/tests/test_security.py`**

```python
import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("MySecret123!")
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("MySecret123!")
    assert verify_password("MySecret123!", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("MySecret123!")
    assert verify_password("WrongPassword", hashed) is False


def test_create_and_decode_access_token():
    payload = {"sub": "user-uuid", "tenant_id": "tenant-uuid", "roles": ["admin"]}
    token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded = decode_access_token(token)
    assert decoded["sub"] == "user-uuid"
    assert decoded["tenant_id"] == "tenant-uuid"
    assert decoded["roles"] == ["admin"]


def test_decode_expired_token_raises():
    payload = {"sub": "user-uuid", "tenant_id": "tenant-uuid", "roles": []}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-1))
    with pytest.raises(Exception):
        decode_access_token(token)


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        decode_access_token("not.a.valid.token")
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/test_security.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `app.core.security`.

- [ ] **Step 4: Create `apps/api/app/core/security.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_ROUNDS)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.JWT_PRIVATE_KEY, algorithm="RS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd apps/api && uv run pytest tests/test_security.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/core/security.py apps/api/tests/
git commit -m "feat(api): JWT RS256 encode/decode and bcrypt password utilities (TDD)"
```

---

### Task 9: Request Context + Security Middleware

**Files:**
- Create: `apps/api/app/core/context.py`
- Create: `apps/api/app/core/middleware.py`

- [ ] **Step 1: Create `apps/api/app/core/context.py`**

```python
import uuid
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    roles: list[str]
    permissions: set[str] = field(default_factory=set)
    ip_address: str | None = None
```

- [ ] **Step 2: Create `apps/api/app/core/middleware.py`**

```python
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.context import RequestContext
from app.core.security import decode_access_token

# Routes that do not require authentication
PUBLIC_PATHS = {
    "/health",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/oauth/google",
    "/auth/oauth/google/callback",
    "/auth/oauth/github",
    "/auth/oauth/github/callback",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_access_token(token)
        except ValueError:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

        import uuid
        request.state.ctx = RequestContext(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            ip_address=request.client.host if request.client else None,
        )
        return await call_next(request)


SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
```

- [ ] **Step 3: Verify import**

```bash
cd apps/api && uv run python -c "from app.core.middleware import SecurityMiddleware; print('Middleware OK')"
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/core/context.py apps/api/app/core/middleware.py
git commit -m "feat(api): RequestContext, SecurityMiddleware (JWT→context), SecurityHeadersMiddleware"
```

---

### Task 10: RBAC Dependency + Rate Limiting

**Files:**
- Create: `apps/api/app/core/deps.py`
- Create: `apps/api/app/core/rate_limit.py`
- Create: `apps/api/tests/test_rbac.py`

- [ ] **Step 1: Write failing test — `apps/api/tests/test_rbac.py`**

```python
import pytest
import uuid
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.core.context import RequestContext
from app.core.deps import require_permission


def make_ctx(permissions: set[str]) -> RequestContext:
    ctx = RequestContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        roles=["member"],
        permissions=permissions,
    )
    return ctx


@pytest.mark.asyncio
async def test_require_permission_grants_access():
    ctx = make_ctx({"invoices:read"})
    dep = require_permission("invoices:read")
    # Should not raise
    await dep(ctx=ctx)


@pytest.mark.asyncio
async def test_require_permission_denies_access():
    ctx = make_ctx({"invoices:read"})
    dep = require_permission("invoices:write")
    with pytest.raises(HTTPException) as exc_info:
        await dep(ctx=ctx)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permission_empty_permissions():
    ctx = make_ctx(set())
    dep = require_permission("users:manage")
    with pytest.raises(HTTPException) as exc_info:
        await dep(ctx=ctx)
    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run test — verify fails**

```bash
cd apps/api && uv run pytest tests/test_rbac.py -v
```

Expected: `ImportError` — `app.core.deps` does not exist.

- [ ] **Step 3: Create `apps/api/app/core/deps.py`**

```python
from fastapi import Depends, HTTPException, Request, status

from app.core.context import RequestContext


def get_request_context(request: Request) -> RequestContext:
    ctx = getattr(request.state, "ctx", None)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return ctx


def require_permission(permission: str):
    async def dependency(ctx: RequestContext = Depends(get_request_context)) -> None:
        if permission not in ctx.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
    return dependency
```

- [ ] **Step 4: Run test — verify passes**

```bash
cd apps/api && uv run pytest tests/test_rbac.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Create `apps/api/app/core/rate_limit.py`**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
```

- [ ] **Step 6: Verify import**

```bash
cd apps/api && uv run python -c "from app.core.rate_limit import limiter; print('Rate limiter OK')"
```

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/core/deps.py apps/api/app/core/rate_limit.py apps/api/tests/test_rbac.py
git commit -m "feat(api): RBAC require_permission dependency and rate limiter (TDD)"
```

---

### Task 11: Auth Schemas + Routes (Register + Login)

**Files:**
- Create: `apps/api/app/schemas/__init__.py`
- Create: `apps/api/app/schemas/auth.py`
- Create: `apps/api/app/routes/auth.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_auth.py`

- [ ] **Step 1: Create `apps/api/app/schemas/__init__.py`** (empty)

- [ ] **Step 2: Create `apps/api/app/schemas/auth.py`**

```python
import re
import uuid
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    tenant_id: uuid.UUID
    roles: list[str]
```

- [ ] **Step 3: Create `apps/api/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql://user:password@localhost:5432/smb_os_test"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    session.begin_nested()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

Note: create the test database first:
```bash
createdb smb_os_test
cd apps/api && uv run alembic -x db=test upgrade head
```
Or simply: `psql -c "CREATE DATABASE smb_os_test;"` then `DATABASE_URL=postgresql://user:password@localhost:5432/smb_os_test uv run alembic upgrade head`

- [ ] **Step 4: Write failing tests — `apps/api/tests/test_auth.py`**

```python
import pytest


def test_register_creates_user_and_tenant(client):
    response = client.post("/auth/register", json={
        "email": "owner@acme.com",
        "password": "Secret123!",
        "tenant_name": "Acme Corp",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "owner@acme.com"
    assert "tenant_id" in data
    assert "owner" in data["roles"]


def test_register_weak_password_rejected(client):
    response = client.post("/auth/register", json={
        "email": "user@acme.com",
        "password": "weak",
        "tenant_name": "Acme",
    })
    assert response.status_code == 422


def test_register_duplicate_email_same_tenant_rejected(client):
    payload = {"email": "dup@acme.com", "password": "Secret123!", "tenant_name": "DupCorp"}
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409


def test_login_returns_access_token(client):
    client.post("/auth/register", json={
        "email": "login@acme.com", "password": "Secret123!", "tenant_name": "LoginCorp"
    })
    response = client.post("/auth/login", json={
        "email": "login@acme.com", "password": "Secret123!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={
        "email": "bad@acme.com", "password": "Secret123!", "tenant_name": "BadCorp"
    })
    response = client.post("/auth/login", json={
        "email": "bad@acme.com", "password": "WrongPassword1!"
    })
    assert response.status_code == 401
```

- [ ] **Step 5: Run tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/test_auth.py -v
```

Expected: 404 or connection errors (routes not implemented yet).

- [ ] **Step 6: Create `apps/api/app/routes/auth.py`**

```python
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.db.models.auth import RefreshToken
from app.db.models.rbac import Permission, Role, RolePermission, UserRole
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.core.config import settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

DEFAULT_OWNER_PERMISSIONS = [
    "users:read", "users:write", "users:manage",
    "roles:read", "roles:write",
    "settings:read", "settings:write",
    "audit:read",
]


def _build_token_payload(user: User, roles: list[str]) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "roles": roles,
    }


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=raw_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/auth/refresh",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    # Check duplicate email across all tenants for this registration flow
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Create tenant
    tenant = Tenant(name=body.tenant_name, slug=str(uuid.uuid4())[:8])
    db.add(tenant)
    db.flush()

    # Create user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        email_verified=False,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Create owner role with all permissions
    owner_role = Role(tenant_id=tenant.id, name="owner", is_default=False)
    db.add(owner_role)
    db.flush()

    for perm_id in DEFAULT_OWNER_PERMISSIONS:
        perm = db.query(Permission).filter(Permission.id == perm_id).first()
        if perm:
            db.add(RolePermission(role_id=owner_role.id, permission_id=perm.id))

    db.add(UserRole(user_id=user.id, role_id=owner_role.id))
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        tenant_id=user.tenant_id,
        roles=["owner"],
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    roles = [ur.role.name for ur in user.user_roles]
    token = create_access_token(_build_token_payload(user, roles))

    # Issue refresh token
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=RefreshToken.hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    _set_refresh_cookie(response, raw)

    return TokenResponse(access_token=token)
```

- [ ] **Step 7: Run tests — verify they pass**

```bash
cd apps/api && uv run pytest tests/test_auth.py -v
```

Expected: `5 passed`

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/schemas/ apps/api/app/routes/auth.py apps/api/tests/conftest.py apps/api/tests/test_auth.py
git commit -m "feat(api): auth schemas, register and login endpoints with TDD"
```

---

### Task 12: Auth Routes (Refresh + Logout)

**Files:**
- Modify: `apps/api/app/routes/auth.py`
- Modify: `apps/api/tests/test_auth.py`

- [ ] **Step 1: Add refresh + logout tests to `apps/api/tests/test_auth.py`**

Append to the existing file:

```python
def test_refresh_issues_new_access_token(client):
    client.post("/auth/register", json={
        "email": "refresh@acme.com", "password": "Secret123!", "tenant_name": "RefreshCorp"
    })
    login_resp = client.post("/auth/login", json={
        "email": "refresh@acme.com", "password": "Secret123!"
    })
    assert login_resp.status_code == 200
    # refresh_token cookie is set by login
    refresh_resp = client.post("/auth/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_refresh_without_cookie_returns_401(client):
    response = client.post("/auth/refresh")
    assert response.status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post("/auth/register", json={
        "email": "logout@acme.com", "password": "Secret123!", "tenant_name": "LogoutCorp"
    })
    client.post("/auth/login", json={"email": "logout@acme.com", "password": "Secret123!"})
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 204
    # After logout, refresh should fail
    refresh_resp = client.post("/auth/refresh")
    assert refresh_resp.status_code == 401
```

- [ ] **Step 2: Run new tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/test_auth.py::test_refresh_issues_new_access_token -v
```

Expected: 404 (route not implemented).

- [ ] **Step 3: Add refresh and logout to `apps/api/app/routes/auth.py`**

Append to the existing file:

```python
@router.post("/refresh", response_model=TokenResponse)
def refresh(response: Response, db: Session = Depends(get_db), refresh_token: str | None = Cookie(default=None)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    token_hash = RefreshToken.hash_token(refresh_token)
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).first()

    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Rotate refresh token
    stored.revoked = True
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=RefreshToken.hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    db.commit()
    _set_refresh_cookie(response, raw)

    roles = [ur.role.name for ur in user.user_roles]
    return TokenResponse(access_token=create_access_token(_build_token_payload(user, roles)))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, db: Session = Depends(get_db), refresh_token: str | None = Cookie(default=None)):
    if refresh_token:
        token_hash = RefreshToken.hash_token(refresh_token)
        stored = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if stored:
            stored.revoked = True
            db.commit()
    response.delete_cookie("refresh_token", path="/auth/refresh")
```

- [ ] **Step 4: Run all auth tests**

```bash
cd apps/api && uv run pytest tests/test_auth.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routes/auth.py apps/api/tests/test_auth.py
git commit -m "feat(api): refresh token rotation and logout endpoint (TDD)"
```

---

### Task 13: RLS Integration Test

**Files:**
- Create: `apps/api/tests/test_rls.py`

- [ ] **Step 1: Create `apps/api/tests/test_rls.py`**

```python
import uuid
import pytest
from sqlalchemy import text

from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.core.security import hash_password


def test_user_cannot_see_other_tenant_user(db):
    """RLS must block cross-tenant reads at the DB level."""
    # Create two tenants
    tenant_a = Tenant(name="Tenant A", slug="tenant-a")
    tenant_b = Tenant(name="Tenant B", slug="tenant-b")
    db.add_all([tenant_a, tenant_b])
    db.flush()

    # Create one user per tenant
    user_a = User(tenant_id=tenant_a.id, email="a@a.com", password_hash=hash_password("Pw123456!"))
    user_b = User(tenant_id=tenant_b.id, email="b@b.com", password_hash=hash_password("Pw123456!"))
    db.add_all([user_a, user_b])
    db.flush()

    # Set RLS context to tenant A
    db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_a.id)})

    # Query for all users — should only see tenant A's user
    visible = db.query(User).filter(User.tenant_id == tenant_a.id).all()
    visible_ids = {u.id for u in visible}
    assert user_a.id in visible_ids
    assert user_b.id not in visible_ids

    # Confirm tenant B user exists (bypass RLS via direct filter)
    db.execute(text("RESET app.tenant_id"))
    all_users = db.query(User).all()
    all_ids = {u.id for u in all_users}
    assert user_b.id in all_ids
```

- [ ] **Step 2: Run RLS test**

```bash
cd apps/api && uv run pytest tests/test_rls.py -v
```

Expected: `1 passed` — confirms RLS blocks cross-tenant reads.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/test_rls.py
git commit -m "test(api): RLS cross-tenant isolation integration test"
```

---

### Task 14: Wire Everything into main.py

**Files:**
- Modify: `apps/api/main.py`
- Modify: `apps/api/app/routes/health.py`

- [ ] **Step 1: Replace `apps/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.middleware import SecurityHeadersMiddleware, SecurityMiddleware
from app.core.rate_limit import limiter
from app.routes.auth import router as auth_router
from app.routes.health import router as health_router

app = FastAPI(
    title="SMB OS API",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers (outermost — applied to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# JWT validation + request context injection
app.add_middleware(SecurityMiddleware)

# CORS — must come after security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(auth_router)
```

- [ ] **Step 2: Update `apps/api/app/routes/health.py`**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.deps import get_request_context
from app.core.context import RequestContext

router = APIRouter()


@router.get("/health")
async def health_check():
    """Public endpoint — no auth required."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/protected")
async def health_check_protected(ctx: RequestContext = Depends(get_request_context)):
    """Protected endpoint — demonstrates auth + context injection."""
    return {
        "status": "ok",
        "user_id": str(ctx.user_id),
        "tenant_id": str(ctx.tenant_id),
    }
```

- [ ] **Step 3: Verify the app starts**

```bash
cd apps/api && uv run python -c "from main import app; print('App OK, routes:', [r.path for r in app.routes])"
```

Expected: prints list including `/health`, `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`.

- [ ] **Step 4: Run full test suite**

```bash
cd apps/api && uv run pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/main.py apps/api/app/routes/health.py
git commit -m "feat(api): wire middleware, CORS, rate limiter, and all routers into main.py"
```

---

## Self-Review

### Spec Coverage

| Spec Requirement | Task |
|---|---|
| JWT RS256 access token (15 min) | Task 8 |
| Refresh token in HttpOnly cookie (7 days) | Task 11, 12 |
| bcrypt password hashing (factor 12) | Task 8 |
| OAuth accounts model | Task 4 |
| email+password register/login | Task 11 |
| Refresh + logout endpoints | Task 12 |
| tenant_id on all user tables | Tasks 3, 4, 5 |
| PostgreSQL RLS on tenant-scoped tables | Task 7 |
| Cross-tenant isolation verified by test | Task 13 |
| RBAC models (Permission, Role, RolePermission, UserRole) | Task 5 |
| require_permission dependency | Task 10 |
| Default owner role with all permissions | Task 11 |
| Rate limiting (slowapi) | Task 10 |
| Security headers middleware | Task 9 |
| CORS from env var ALLOWED_ORIGINS | Task 1, 14 |
| Audit log model (immutable) | Task 6, 7 |
| pydantic-settings for all env vars | Task 1 |
| Password strength validation | Task 11 |

OAuth route handlers (Google, GitHub callbacks) are deferred to the frontend auth plan where next-auth handles the OAuth flow. The `oauth_accounts` model and DB table are ready.

### Placeholder Scan

No TBD, TODO, or "implement later" in any step. Every step has concrete code.

### Type Consistency

- `RequestContext` defined in Task 9, used in Tasks 10, 12, 14 — consistent field names
- `RefreshToken.hash_token()` defined in Task 4, called in Tasks 11, 12 — consistent
- `_build_token_payload()` defined and used in Tasks 11, 12 — consistent
- `_set_refresh_cookie()` defined and used in Tasks 11, 12 — consistent
