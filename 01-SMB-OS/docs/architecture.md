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
