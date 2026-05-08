# SMB OS — Security Layer Design

**Date:** 2026-04-25
**Status:** Approved
**Scope:** Authentication, multi-tenancy, RBAC, security hardening (frontend + backend)

---

## 1. Goals

- All user data isolated by tenant at the database level — no cross-tenant leakage possible even if the API has a bug
- Authentication via email+password and OAuth (Google, GitHub)
- Role-Based Access Control with granular permissions per resource
- Zero secrets in code — all configuration via environment variables
- CCPA-ready data practices for the US market

## 2. Architecture Overview

Security is enforced in three independent layers. A request must pass all three before touching business logic.

```
Request
  │
  ▼
[Layer 1] SecurityMiddleware (FastAPI)
  - Validates JWT signature and expiry
  - Extracts tenant_id, user_id, roles from token
  - Injects RequestContext into every request
  - Rejects with 401 if token invalid or missing
  │
  ▼
[Layer 2] RBAC Dependency (per endpoint)
  - require_permission("resource:action")
  - Checks user has permission within their tenant
  - Rejects with 403 if permission missing
  │
  ▼
[Layer 3] PostgreSQL Row Level Security
  - SET app.tenant_id = '{tenant_id}' on every DB connection
  - RLS policy: WHERE tenant_id = current_setting('app.tenant_id')
  - Database rejects cross-tenant reads/writes at storage level
  │
  ▼
Business Logic (routers, services)
```

## 3. Authentication

### 3.1 Email + Password

- Passwords hashed with **bcrypt**, cost factor 12
- Registration requires email verification (token sent via email)
- Login returns:
  - `access_token` (JWT, 15 minutes) — in response body for API clients
  - `refresh_token` (opaque, 7 days) — in `HttpOnly; Secure; SameSite=Strict` cookie
- Refresh endpoint issues new access token without re-login
- Failed login attempts: rate-limited to 5 attempts per 15 minutes per IP

### 3.2 OAuth (Google, GitHub)

- Handled by **authlib** (backend) and **next-auth** (frontend)
- OAuth callback creates or links account to existing email
- Same JWT + refresh cookie flow after OAuth completes
- OAuth accounts cannot set a local password unless explicitly requested

### 3.3 JWT Structure

```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "email": "user@example.com",
  "roles": ["admin"],
  "iat": 1714000000,
  "exp": 1714000900
}
```

- Signed with **RS256** (asymmetric) — public key verifiable by any service
- Secret key stored in env var `JWT_PRIVATE_KEY` — never in code

### 3.4 Token Storage (Frontend)

- `access_token`: memory only (React state / next-auth session) — never localStorage
- `refresh_token`: `HttpOnly; Secure; SameSite=Strict` cookie — JavaScript cannot read it
- Axios interceptor: if 401, auto-calls `/auth/refresh`, retries original request

## 4. Multi-Tenancy

### 4.1 Data Model

Every tenant-scoped table has:
```sql
tenant_id UUID NOT NULL REFERENCES tenants(id)
```

No exceptions. Enforced via SQLAlchemy base model mixin.

### 4.2 PostgreSQL Row Level Security

Every tenant-scoped table has RLS enabled:

```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON invoices
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

The API sets the tenant context on every connection before any query:
```python
session.execute(text("SET app.tenant_id = :tid"), {"tid": str(ctx.tenant_id)})
```

This means: even if a developer forgets to filter by `tenant_id` in a query, PostgreSQL blocks the result. Defense in depth.

### 4.3 Tenant Resolution

Tenant is always resolved from the **JWT** — never from a URL parameter, header, or request body. A user cannot forge their tenant context.

## 5. Role-Based Access Control (RBAC)

### 5.1 Data Model

```
tenants
  └── roles (tenant-scoped, customizable)
        └── role_permissions (role → permission)
  └── users
        └── user_roles (user → role, within tenant)

permissions (global registry)
  - id: string  e.g. "invoices:read", "invoices:write", "users:manage"
```

### 5.2 Permission Format

`resource:action` — examples:
- `invoices:read`
- `invoices:write`
- `invoices:delete`
- `users:read`
- `users:manage`
- `settings:write`
- `reports:export`

### 5.3 Endpoint Declaration

```python
@router.get("/invoices")
async def list_invoices(
    ctx: RequestContext = Depends(get_request_context),
    _: None = Depends(require_permission("invoices:read")),
):
    ...
```

`require_permission` checks `ctx.permissions` (loaded from DB at auth time, cached in JWT). Returns 403 if missing.

### 5.4 Default Roles

| Role | Permissions |
|------|-------------|
| `owner` | All permissions |
| `admin` | All except billing |
| `member` | Read-only by default, configurable |

Roles are tenant-scoped — an `admin` in Tenant A has no access to Tenant B.

## 6. Security Hardening

### 6.1 Rate Limiting (slowapi)

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 5/15min per IP |
| `POST /auth/register` | 10/hour per IP |
| `POST /auth/refresh` | 30/min per IP |
| All other endpoints | 100/min per user |

### 6.2 Security Headers (FastAPI middleware)

```
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; ...
```

### 6.3 CORS

```python
allow_origins = settings.ALLOWED_ORIGINS  # from env var, comma-separated
allow_credentials = True
allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
allow_headers = ["Authorization", "Content-Type"]
```

Never `allow_origins=["*"]` in any environment.

### 6.4 Input Validation

- Every endpoint uses **Pydantic v2** models for request bodies
- No raw dict/JSON access anywhere
- File uploads: validated mime type + size limit (10MB default)
- Query parameters: typed and bounded (e.g. `limit: int = Query(default=20, le=100)`)

### 6.5 Password Policy

- Minimum 8 characters
- At least 1 uppercase, 1 lowercase, 1 digit
- Checked via Pydantic validator on registration and password change
- Breach detection via HaveIBeenPwned API (optional, off by default)

### 6.6 Audit Log

Immutable append-only table:

```sql
CREATE TABLE audit_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL,
  user_id     UUID NOT NULL,
  action      TEXT NOT NULL,   -- e.g. "invoice.created"
  resource_id UUID,
  payload     JSONB,
  ip_address  INET,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No UPDATE or DELETE allowed (enforced via RLS policy)
CREATE POLICY audit_log_no_delete ON audit_log FOR DELETE USING (false);
CREATE POLICY audit_log_no_update ON audit_log FOR UPDATE USING (false);
```

Every write operation (create, update, delete) automatically logs via a SQLAlchemy event listener.

### 6.7 Secrets Management

All secrets via environment variables. No defaults in code for production values.

Required env vars:
```
JWT_PRIVATE_KEY=       # RS256 private key (PEM)
JWT_PUBLIC_KEY=        # RS256 public key (PEM)
DATABASE_URL=          # PostgreSQL connection string
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
ALLOWED_ORIGINS=       # comma-separated list
SECRET_KEY=            # for cookie signing
```

## 7. Frontend Security (Next.js)

### 7.1 Route Protection

Next.js middleware (`middleware.ts`) intercepts all requests:
- Public routes: `/`, `/auth/login`, `/auth/register`, `/auth/callback/*`
- All other routes: redirect to `/auth/login` if no valid session

### 7.2 next-auth Configuration

- `session.strategy: "jwt"` — session stored in signed cookie, not DB
- `cookies.sessionToken`: `HttpOnly; Secure; SameSite=Strict`
- Providers: Credentials (email+password), Google, GitHub

### 7.3 API Client

Axios instance with:
- Base URL from `NEXT_PUBLIC_API_URL`
- Authorization header injected from session token
- 401 interceptor: auto-refresh token, retry once, then redirect to login

### 7.4 Security Headers (Next.js)

Configured in `next.config.ts`:
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: (strict, defined per environment)
```

## 8. Database Schema (Core Security Tables)

```sql
-- Tenants
CREATE TABLE tenants (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  slug        TEXT UNIQUE NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Users
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  email           TEXT NOT NULL,
  password_hash   TEXT,              -- null for OAuth-only accounts
  email_verified  BOOLEAN NOT NULL DEFAULT false,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, email)
);

-- OAuth accounts linked to users
CREATE TABLE oauth_accounts (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  provider    TEXT NOT NULL,         -- 'google' | 'github'
  provider_id TEXT NOT NULL,
  UNIQUE (provider, provider_id)
);

-- Permissions registry
CREATE TABLE permissions (
  id   TEXT PRIMARY KEY             -- 'invoices:read'
);

-- Roles (tenant-scoped)
CREATE TABLE roles (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL REFERENCES tenants(id),
  name        TEXT NOT NULL,
  is_default  BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (tenant_id, name)
);

-- Role → Permission
CREATE TABLE role_permissions (
  role_id       UUID NOT NULL REFERENCES roles(id),
  permission_id TEXT NOT NULL REFERENCES permissions(id),
  PRIMARY KEY (role_id, permission_id)
);

-- User → Role (within tenant)
CREATE TABLE user_roles (
  user_id UUID NOT NULL REFERENCES users(id),
  role_id UUID NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);

-- Refresh tokens
CREATE TABLE refresh_tokens (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id),
  token_hash  TEXT NOT NULL UNIQUE,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked     BOOLEAN NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 9. File Structure Changes

```
apps/api/
  app/
    core/
      config.py          # Settings (pydantic-settings, reads env vars)
      security.py        # JWT encode/decode, password hashing
      middleware.py      # SecurityMiddleware, SecurityHeadersMiddleware
      context.py         # RequestContext dataclass
      deps.py            # get_request_context, require_permission
      rate_limit.py      # slowapi limiter config
    db/
      base.py            # SQLAlchemy engine + session factory
      models/
        tenant.py
        user.py
        auth.py          # refresh_tokens, oauth_accounts
        rbac.py          # roles, permissions, role_permissions, user_roles
        audit.py         # audit_log
      migrations/        # Alembic
    routes/
      auth.py            # /auth/login, /register, /refresh, /logout, /oauth/*
      health.py          # (existing)
    main.py              # updated: registers middleware + routers

apps/web/
  src/
    lib/
      auth.ts            # next-auth config
      api.ts             # axios instance with interceptors
    middleware.ts         # Next.js route protection
    app/
      auth/
        login/page.tsx
        register/page.tsx

packages/types/
  src/
    auth.ts              # AuthUser, Session, Permission types (shared)
```

## 10. Out of Scope (This Iteration)

- Email sending infrastructure (needed for email verification — placeholder only)
- Billing / subscription management
- 2FA / TOTP
- IP allowlisting
- SAML/Enterprise SSO
