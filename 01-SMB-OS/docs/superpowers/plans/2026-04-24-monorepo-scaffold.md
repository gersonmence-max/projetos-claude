# SMB-OS Monorepo Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the smb-os (Small and Medium Business Operating System) monorepo with root config, shared packages (types, utils, ui), a Next.js web app, and a FastAPI backend.

**Architecture:** pnpm workspaces for package management, Turborepo for task orchestration. TypeScript packages are consumed by the Next.js web app. FastAPI runs independently in Python. Mobile (Expo) is deferred.

**Tech Stack:** pnpm 9+, Turborepo 2+, Next.js 14 (App Router), TypeScript 5, FastAPI 0.110+, Python 3.11+, uv

---

## File Map

**Root**
- `package.json` — workspace root with Turborepo scripts
- `pnpm-workspace.yaml` — workspace globs
- `turbo.json` — Turborepo pipeline config
- `tsconfig.base.json` — base TS config extended by all packages
- `.gitignore` — Node, Python, Next.js ignores
- `.env.example` — documented environment variables
- `README.md` — project overview

**packages/types**
- `packages/types/package.json`
- `packages/types/tsconfig.json`
- `packages/types/src/api.ts` — shared API response interfaces
- `packages/types/src/index.ts` — barrel export

**packages/utils**
- `packages/utils/package.json`
- `packages/utils/tsconfig.json`
- `packages/utils/src/format.ts` — date, currency, slug helpers
- `packages/utils/src/index.ts` — barrel export

**packages/ui**
- `packages/ui/package.json`
- `packages/ui/tsconfig.json`
- `packages/ui/src/Button.tsx` — stub Button component
- `packages/ui/src/index.ts` — barrel export

**apps/web**
- `apps/web/package.json`
- `apps/web/next.config.ts`
- `apps/web/tsconfig.json`
- `apps/web/src/app/layout.tsx`
- `apps/web/src/app/page.tsx`

**apps/api**
- `apps/api/pyproject.toml`
- `apps/api/.python-version`
- `apps/api/main.py` — FastAPI entry point
- `apps/api/app/__init__.py`
- `apps/api/app/routes/__init__.py`
- `apps/api/app/routes/health.py` — health check route

**docs**
- `docs/architecture.md`

---

### Task 1: Root Monorepo Config

**Files:**
- Create: `package.json`
- Create: `pnpm-workspace.yaml`
- Create: `turbo.json`
- Create: `tsconfig.base.json`
- Create: `.gitignore`

- [ ] **Step 1: Verify prerequisites**

```bash
node --version    # Expected: v20.x.x or higher
pnpm --version    # Expected: 9.x.x
```

If pnpm is missing: `npm install -g pnpm`

- [ ] **Step 2: Initialize git**

```bash
git init
```

Expected: `Initialized empty Git repository in .../smb-os/.git/`

- [ ] **Step 3: Create `package.json`**

```json
{
  "name": "smb-os",
  "private": true,
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "lint": "turbo run lint",
    "type-check": "turbo run type-check",
    "clean": "turbo run clean"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.4.0"
  },
  "packageManager": "pnpm@9.0.0",
  "engines": {
    "node": ">=20"
  }
}
```

- [ ] **Step 4: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "apps/*"
  - "packages/*"
```

- [ ] **Step 5: Create `turbo.json`**

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "type-check": {
      "dependsOn": ["^build"]
    },
    "clean": {
      "cache": false
    }
  }
}
```

- [ ] **Step 6: Create `tsconfig.base.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```

- [ ] **Step 7: Create `.gitignore`**

```
# Dependencies
node_modules/
.pnpm-store/

# Build outputs
dist/
.next/
out/
build/

# Python
__pycache__/
*.pyc
*.pyo
.venv/

# Env
.env
.env.local
.env.*.local

# Misc
.DS_Store
*.log
.turbo/
```

- [ ] **Step 8: Install root dependencies**

```bash
pnpm install
```

Expected: `node_modules/` and `pnpm-lock.yaml` created.

- [ ] **Step 9: Commit**

```bash
git add package.json pnpm-workspace.yaml turbo.json tsconfig.base.json .gitignore pnpm-lock.yaml
git commit -m "chore: initialize monorepo with pnpm workspaces and Turborepo"
```

---

### Task 2: packages/types

**Files:**
- Create: `packages/types/package.json`
- Create: `packages/types/tsconfig.json`
- Create: `packages/types/src/api.ts`
- Create: `packages/types/src/index.ts`

- [ ] **Step 1: Create directory**

```bash
mkdir -p packages/types/src
```

- [ ] **Step 2: Create `packages/types/package.json`**

```json
{
  "name": "@smb-os/types",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Create `packages/types/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `packages/types/src/api.ts`**

```typescript
export interface ApiResponse<T> {
  data: T;
  error: string | null;
  status: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number;
  page: number;
  pageSize: number;
}

export interface HealthCheckResponse {
  status: "ok" | "degraded" | "down";
  timestamp: string;
}
```

- [ ] **Step 5: Create `packages/types/src/index.ts`**

```typescript
export * from "./api";
```

- [ ] **Step 6: Run type-check**

```bash
cd packages/types && pnpm type-check
```

Expected: No output (zero errors).

- [ ] **Step 7: Commit**

```bash
cd ../..
git add packages/types/
git commit -m "feat(packages): add @smb-os/types package"
```

---

### Task 3: packages/utils

**Files:**
- Create: `packages/utils/package.json`
- Create: `packages/utils/tsconfig.json`
- Create: `packages/utils/src/format.ts`
- Create: `packages/utils/src/index.ts`

- [ ] **Step 1: Create directory**

```bash
mkdir -p packages/utils/src
```

- [ ] **Step 2: Create `packages/utils/package.json`**

```json
{
  "name": "@smb-os/utils",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@smb-os/types": "workspace:*"
  },
  "devDependencies": {
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Create `packages/utils/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `packages/utils/src/format.ts`**

```typescript
export function formatDate(date: Date | string): string {
  return new Date(date).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function formatCurrency(value: number, currency = "BRL"): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
  }).format(value);
}

export function slugify(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}
```

- [ ] **Step 5: Create `packages/utils/src/index.ts`**

```typescript
export * from "./format";
```

- [ ] **Step 6: Install and type-check**

```bash
pnpm install && cd packages/utils && pnpm type-check
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
cd ../..
git add packages/utils/
git commit -m "feat(packages): add @smb-os/utils package"
```

---

### Task 4: packages/ui

**Files:**
- Create: `packages/ui/package.json`
- Create: `packages/ui/tsconfig.json`
- Create: `packages/ui/src/Button.tsx`
- Create: `packages/ui/src/index.ts`

- [ ] **Step 1: Create directory**

```bash
mkdir -p packages/ui/src
```

- [ ] **Step 2: Create `packages/ui/package.json`**

```json
{
  "name": "@smb-os/ui",
  "version": "0.0.1",
  "private": true,
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "type-check": "tsc --noEmit"
  },
  "peerDependencies": {
    "react": "^18 || ^19",
    "react-dom": "^18 || ^19"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "react": "^18.3.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Create `packages/ui/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "jsx": "react-jsx",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `packages/ui/src/Button.tsx`**

```tsx
import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({
  variant = "primary",
  size = "md",
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant} btn-${size} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 5: Create `packages/ui/src/index.ts`**

```typescript
export { Button } from "./Button";
```

- [ ] **Step 6: Install and type-check**

```bash
pnpm install && cd packages/ui && pnpm type-check
```

Expected: No errors.

- [ ] **Step 7: Commit**

```bash
cd ../..
git add packages/ui/
git commit -m "feat(packages): add @smb-os/ui package"
```

---

### Task 5: apps/web (Next.js)

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`

- [ ] **Step 1: Create directory**

```bash
mkdir -p apps/web/src/app
```

- [ ] **Step 2: Create `apps/web/package.json`**

```json
{
  "name": "@smb-os/web",
  "version": "0.0.1",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "@smb-os/types": "workspace:*",
    "@smb-os/ui": "workspace:*",
    "@smb-os/utils": "workspace:*",
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.4.0"
  }
}
```

- [ ] **Step 3: Create `apps/web/tsconfig.json`**

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create `apps/web/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@smb-os/ui", "@smb-os/utils", "@smb-os/types"],
};

export default nextConfig;
```

- [ ] **Step 5: Create `apps/web/src/app/layout.tsx`**

```tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SMB OS",
  description: "Small and Medium Business Operating System",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Create `apps/web/src/app/page.tsx`**

```tsx
export default function HomePage() {
  return (
    <main>
      <h1>SMB OS</h1>
      <p>Small and Medium Business Operating System</p>
    </main>
  );
}
```

- [ ] **Step 7: Install dependencies**

```bash
pnpm install
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd apps/web && pnpm dev
```

Expected: `▲ Next.js 14.x.x` and `Local: http://localhost:3000` within 15 seconds. Then Ctrl+C.

- [ ] **Step 9: Commit**

```bash
cd ../..
git add apps/web/
git commit -m "feat(web): scaffold Next.js app with shared package integration"
```

---

### Task 6: apps/api (FastAPI)

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/.python-version`
- Create: `apps/api/main.py`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/routes/__init__.py`
- Create: `apps/api/app/routes/health.py`

- [ ] **Step 1: Verify prerequisites**

```bash
python --version    # Expected: Python 3.11+
uv --version        # Expected: uv 0.x.x
```

If uv is missing: `pip install uv` or visit https://docs.astral.sh/uv/

- [ ] **Step 2: Create directory**

```bash
mkdir -p apps/api/app/routes
```

- [ ] **Step 3: Create `apps/api/.python-version`**

```
3.11
```

- [ ] **Step 4: Create `apps/api/pyproject.toml`**

```toml
[project]
name = "smb-os-api"
version = "0.0.1"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "httpx>=0.27.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 5: Create `apps/api/app/__init__.py`**

Create an empty file at `apps/api/app/__init__.py`.

- [ ] **Step 6: Create `apps/api/app/routes/__init__.py`**

Create an empty file at `apps/api/app/routes/__init__.py`.

- [ ] **Step 7: Create `apps/api/app/routes/health.py`**

```python
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 8: Create `apps/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router

app = FastAPI(title="SMB OS API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
```

- [ ] **Step 9: Create virtual environment and install**

```bash
cd apps/api && uv sync
```

Expected: `.venv/` created and packages installed.

- [ ] **Step 10: Verify API starts**

```bash
cd apps/api && uv run uvicorn main:app --reload --port 8000
```

Expected: `Application startup complete.` listening on `http://localhost:8000`. Then Ctrl+C.

- [ ] **Step 11: Commit**

```bash
cd ../..
git add apps/api/
git commit -m "feat(api): scaffold FastAPI app with health check route"
```

---

### Task 7: Root Files and Docs

**Files:**
- Create: `.env.example`
- Create: `README.md`
- Create: `docs/architecture.md`

- [ ] **Step 1: Create `docs/` directory**

```bash
mkdir -p docs
```

- [ ] **Step 2: Create `.env.example`**

```
# Web
NEXT_PUBLIC_API_URL=http://localhost:8000

# API
DATABASE_URL=postgresql://user:password@localhost:5432/smb_os
SECRET_KEY=change-me-in-production
ENVIRONMENT=development
```

- [ ] **Step 3: Create `README.md`**

```markdown
# SMB OS

> Small and Medium Business Operating System

## Stack

| App | Tech |
|-----|------|
| `apps/web` | Next.js 14, TypeScript |
| `apps/api` | FastAPI, Python 3.11+ |

## Getting Started

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11+
- uv

### Install

```bash
# JS packages
pnpm install

# Python packages
cd apps/api && uv sync
```

### Run development servers

```bash
# Web — http://localhost:3000
pnpm --filter @smb-os/web dev

# API — http://localhost:8000
cd apps/api && uv run uvicorn main:app --reload
```

## Project Structure

```
smb-os/
├── apps/
│   ├── web/        # Next.js frontend
│   └── api/        # FastAPI backend
├── packages/
│   ├── types/      # Shared TypeScript types
│   ├── utils/      # Shared utilities (formatting, slugify)
│   └── ui/         # Shared React components
└── docs/
```
```

- [ ] **Step 4: Create `docs/architecture.md`**

```markdown
# Architecture

## Overview

smb-os is a monorepo managed with pnpm workspaces and Turborepo.

## Apps

- **web** (`apps/web`): Next.js 14 (App Router) frontend. Runs on port 3000 in development.
- **api** (`apps/api`): FastAPI backend. Runs on port 8000 in development.

## Shared Packages

- **@smb-os/types**: TypeScript interfaces shared across web and future mobile.
- **@smb-os/utils**: Pure utility functions — date formatting (`formatDate`), currency (`formatCurrency`), URL slugs (`slugify`).
- **@smb-os/ui**: React component library consumed by web. Components are unstyled stubs; apply CSS classes as needed.

## Communication

Web calls API over HTTP/REST. `NEXT_PUBLIC_API_URL` env var points the web app at the API.

## Deferred

- `apps/mobile` (Expo) — not yet scaffolded.
```

- [ ] **Step 5: Commit**

```bash
git add .env.example README.md docs/
git commit -m "docs: add README, .env.example, and architecture overview"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| `apps/web` (Next.js) | Task 5 |
| `apps/api` (FastAPI) | Task 6 |
| `apps/mobile` (Expo) — deferred | Skipped per spec |
| `packages/types` | Task 2 |
| `packages/utils` | Task 3 |
| `packages/ui` | Task 4 |
| `docs/` | Task 7 |
| `.env.example` | Task 7 |
| `README.md` | Task 7 |

All items covered. Mobile explicitly deferred per spec.

### Placeholder Scan

No TBD/TODO in code. README has a template structure the user will fill in as the project grows — intentional.

### Type Consistency

- `ApiResponse<T>`, `PaginatedResponse<T>`, `HealthCheckResponse` defined in Task 2; not consumed in this scaffold but exported for future use.
- `Button` props defined in Task 4 and exported consistently from `packages/ui/src/index.ts`.
- No cross-task type drift.
