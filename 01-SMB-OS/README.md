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
