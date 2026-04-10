# POMS - Purchase Order Management System

AI-powered purchase order processing pipeline. Receives PO emails, extracts structured data via LLM, validates against a RAG knowledge base, and routes based on the resulting issue tags - auto-approving clean POs, flagging soft issues for human review, and never auto-rejecting.

## Table of Contents

- **[Overview](#overview)**
- **[Architecture](#architecture)**
- **[Why RAG Matters](#why-rag-matters)**
- **[Tech Stack](#tech-stack)**
- **[Prerequisites](#prerequisites)**
- **[Project Setup](#project-setup)**
- **[Running the Application](#running-the-application)**
- **[Sample PO Files](#sample-po-files)**
- **[End-to-End Testing](#end-to-end-testing)**
- **[API Reference](#api-reference)**
- **[Project Structure](#project-structure)**
- **[Testing](#testing)**
- **[CLI Reference (run.sh)](#cli-reference-runsh)**
- **[CI/CD](#cicd)**
- **[Deployment (Azure)](#deployment-azure)**
- **[Disclaimer](#disclaimer)**

## Overview

POMS automates procurement document processing through a multi-stage AI pipeline:

1. **Classify** - Determine if an incoming email contains a purchase order
2. **Extract** - Use an LLM to parse PO data into structured JSON (vendor, line items, amounts, terms)
3. **Validate** - Cross-reference extracted data against database records (deterministic) and a RAG knowledge base (AI-powered)
4. **Route** - Based on validation results, auto-approve, flag for review, or mark for rejection
5. **Respond** - Persist the order, send confirmation/notification emails, and surface in the dashboard

The system combines AI extraction with human oversight: clean POs flow through automatically, while edge cases surface in a review dashboard with full context.

**Supported file formats:** PDF (digital and scanned), XLSX/XLS, PNG/JPG/TIFF images, CSV.

## Architecture

```
Email (Gmail / Webhook)
  │
  ├─ Classify (is this a PO?)
  │
  ├─ Extract (LLM → structured JSON)
  │
  ├─ Validate
  │    ├─ Deterministic (DB lookup: vendor registry, product catalog, policies)
  │    └─ RAG (AI review against knowledge base — adjusts, removes, or adds tags)
  │
  ├─ Route (based on final tags)
  │    ├─ No tags       → AUTO-APPROVED  + confirmation email
  │    ├─ Soft tags only → FLAGGED        + acknowledgment email
  │    └─ Any hard tags  → REJECTED       + acknowledgment email (pending human review)
  │
  └─ Persist (PostgreSQL) + Dashboard (React)
```

**Key principle:** The system auto-approves but **never auto-rejects**. Negative outcomes always require human confirmation.

## Why RAG Matters

In POMS, RAG is the difference between a rigid rule engine and an intelligent assistant that understands business context.

### The problem with deterministic-only validation

The deterministic validator checks extracted PO data against database tables: exact vendor name match, catalog price comparison, spending limit lookup. This catches clear issues but produces false positives:

- A PO from **"Acme Corp"** gets flagged as `VENDOR_FUZZY_MATCH` because the registry lists **"Acme Corporation Ltd"** — but any human would recognize this as the same company.
- A unit price of **EUR 17.50** vs a catalog price of **EUR 15.00** gets flagged as `PRICE_MISMATCH` (16.7% deviation) — but the vendor's framework agreement includes a documented Q4 surcharge that makes this price valid.

Without RAG, both POs would be routed to human review unnecessarily.

### What RAG adds

The RAG validation agent receives the deterministic results and queries a knowledge base containing enriched vendor profiles, framework agreements, pricing policies, and exception rules. It can then:

| Action | Example |
|--------|---------|
| **Remove** a false positive | "Acme Corp" is a documented abbreviation for "Acme Corporation Ltd" — remove `VENDOR_FUZZY_MATCH` |
| **Downgrade** severity | Spending limit exceeded, but policy allows escalation — downgrade `OVER_LIMIT` from HARD to SOFT |
| **Upgrade** severity | Payment terms of Net 60 with no exception on file — upgrade `TERMS_VIOLATION` to HARD |
| **Add** a missed issue | Vendor contract expired last month but grace period applies — add informational tag |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13+, FastAPI, async everywhere |
| AI/LLM | Agno (agent framework), Azure OpenAI (GPT-4o) |
| RAG | LanceDB (vector store, hybrid search: vector + full-text) |
| Embeddings | Azure OpenAI text-embedding-3-large (3072 dim) |
| Database | PostgreSQL 18, SQLModel + asyncpg, Alembic (auto-migrate on startup) |
| Email | Gmail API (OAuth2) — polling + sending |
| Frontend | React 19, TypeScript (strict), Vite, TanStack Query, Tailwind CSS 4 |
| Infrastructure | Docker Compose, uv (Python), pnpm (frontend), Ruff (lint/format) |

## Prerequisites

- **Docker & Docker Compose** — for PostgreSQL
- **Python 3.13+** — backend runtime
- **Node.js 20+** — frontend tooling
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[pnpm](https://pnpm.io/)** — frontend package manager
- **Azure OpenAI** — API access for LLM (completion + embeddings)
- **Gmail API credentials** — OAuth2 for email integration (optional, webhook works without it)

## Project Setup

### 1. Clone and install

```bash
git clone <repo-url> && cd poms

# Full setup: starts PostgreSQL, installs backend + frontend deps, creates .env
./run.sh setup
```

Or step by step:

```bash
# Start PostgreSQL
./run.sh up

# Install backend dependencies
./run.sh backend-setup

# Install frontend dependencies
./run.sh frontend-setup
```

### 2. Configure environment

Edit the `.env` file at the project root with your API keys:

```env
# Azure OpenAI — Completion
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name

# Azure OpenAI — Embeddings
AZURE_OPENAI_EMBED_API_KEY=your-key
AZURE_OPENAI_EMBED_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-large

# Gmail (optional — needed for email integration)
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./token.json
AGENT_EMAIL=your-email@gmail.com
```

### 3. Seed reference data and build knowledge base

```bash
# Seed reference data + embed knowledge base in one step
./run.sh kb-init

# Or individually:
./run.sh kb-seed       # Load vendors, catalog, policies into PostgreSQL
./run.sh kb-ingest     # Embed knowledge PDFs into LanceDB for RAG
```

### 4. Gmail setup (optional)

If you want email integration (Gmail polling + sending):

1. Create a Google Cloud project and enable the Gmail API
2. Configure the OAuth consent screen (add your email as a test user)
3. Create OAuth credentials (Desktop application type)
4. Place the downloaded `credentials.json` in `src/backend/`
5. Run the auth flow: `cd src/backend && uv run python -c "import asyncio; from services.email import email_service; asyncio.run(email_service.authenticate())"`
6. Authorize in the browser — `token.json` is saved automatically

## Running the Application

### Start everything (recommended)

```bash
./run.sh dev
```

This starts both the backend (port 8000) and frontend (port 3000) in the same terminal. Press Ctrl+C to stop both.

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Start individually

```bash
# Backend only
./run.sh backend-dev

# Frontend only
./run.sh frontend-dev
```

### What happens on startup

1. Alembic migrations run automatically (database schema is always in sync)
2. The backend connects to the existing LanceDB knowledge base
3. If Gmail credentials are configured, the email poller starts (30s interval)
4. The frontend proxies `/api` requests to the backend

## Sample PO Files

Nine sample POs are included in `assets/samples/`, covering three file formats and three validation scenarios:

| Sample | Format | Vendor | Expected Route | Key Issues |
|--------|--------|--------|----------------|------------|
| `po_clean.pdf` | PDF | Nordic Supply Solutions AB | Auto-approved | All valid, multi-item PLC + safety order |
| `po_fuzzy.pdf` | PDF | Balkan Electr. | Auto-approved (RAG resolves) | Fuzzy vendor match + price deviation |
| `po_bad.pdf` | PDF | Shanghai Dragon Industrial Co. | Rejected | Unknown vendor, no PO#, Net 60, wrong dept |
| `po_clean.xlsx` | XLSX | EuroFasteners GmbH | Auto-approved | 4-item fasteners + cable tray order |
| `po_fuzzy.xlsx` | XLSX | S.Z. Metals | Auto-approved (RAG resolves) | Fuzzy vendor match + copper busbar price |
| `po_bad.xlsx` | XLSX | Omega Industrial Supplies Ltd | Rejected | Unknown vendor, no PO#, GBP, Net 90 |
| `po_clean.png` | Image | Plovdiv Industrial Supply AD | Auto-approved | Lubricants + seal kits, OCR extraction |
| `po_fuzzy.png` | Image | Dutch Logist. BV | Auto-approved (RAG resolves) | Fuzzy vendor match + light curtain price |
| `po_bad.png` | Image | MediterraneanParts SRL | Rejected | Expired contract, no SKUs, Net 45 |

## End-to-End Testing

### Full E2E test (send + poll + pipeline + verify)

```bash
cd src/backend

# Test one sample end-to-end
uv run python -m scripts.test_e2e_email --po clean-pdf

# Test all samples of one format
uv run python -m scripts.test_e2e_email --po pdf

# Test all 9 samples
uv run python -m scripts.test_e2e_email --po all
```

### Pipeline test (no email, direct file processing)

```bash
cd src/backend

# Test all sample files through the pipeline
uv run python -m scripts.test_pipeline

# Test a specific file
uv run python -m scripts.test_pipeline --file ../../assets/samples/po_clean.xlsx
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/webhook/email` | Ingest email payload, triggers pipeline (202) |
| `GET` | `/api/orders/` | List POs (filter by status, vendor; paginated) |
| `GET` | `/api/orders/{id}` | PO detail with validations, tags, emails, logs |
| `POST` | `/api/reviews/{order_id}` | Submit review decision (approve/reject + comment) |
| `GET` | `/api/analytics/` | Dashboard analytics (volume, rates, common tags) |
| `GET` | `/health` | Health check |

Full interactive docs available at http://localhost:8000/docs when the backend is running.

## Project Structure

```
poms/
├── src/
│   ├── backend/
│   │   ├── api/routes/          # HTTP endpoints (orders, reviews, webhook, analytics)
│   │   ├── agent/               # AI pipeline (classifier, extractor, validator, rag_validator, router)
│   │   ├── core/                # Config (BaseSettings), database engine, logging
│   │   ├── models/              # SQLModel database models + enums
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic (email, pipeline, poller, files, knowledge)
│   │   ├── scripts/             # CLI tools (seed data, ingest knowledge, test pipeline)
│   │   ├── migrations/          # Alembic migrations (auto-run on startup)
│   │   └── tests/               # pytest test suite
│   └── frontend/src/
│       ├── api/                 # API client + endpoint functions
│       ├── components/          # UI components (orders, reviews, analytics, layout)
│       ├── hooks/               # TanStack Query hooks (live polling: 2–3s)
│       ├── pages/               # Route pages (dashboard, order detail, analytics)
│       └── types/               # TypeScript interfaces
├── assets/
│   ├── knowledge/           # RAG source data + generated PDFs
│   │   ├── vendors.json     # Approved vendor registry (10 vendors)
│   │   ├── catalog.json     # Product catalog (15 SKUs)
│   │   ├── policies.md      # Corporate procurement policy
│   │   ├── pdfs/            # Generated PDFs for RAG ingestion
│   │   └── generate_pdfs.py # PDF generator script
│   └── samples/             # 9 sample PO files (PDF, XLSX, PNG)
├── docker-compose.yml       # PostgreSQL 18
└── run.sh                   # CLI wrapper for all dev commands
```

## Testing

```bash
# Run all backend tests
./run.sh test

# Run with extra args
./run.sh test -v --cov=backend

# Frontend checks (typecheck + lint + build)
./run.sh frontend-check

# Run everything
./run.sh check
```

## CLI Reference (run.sh)

| Command | Description |
|---------|-------------|
| `./run.sh setup` | Full project setup (DB + deps + .env) |
| `./run.sh dev` | Start backend + frontend together |
| `./run.sh backend-dev` | Start backend only (port 8000) |
| `./run.sh frontend-dev` | Start frontend only (port 3000) |
| `./run.sh up` | Start PostgreSQL |
| `./run.sh down` | Stop services |
| `./run.sh test [args]` | Run pytest with optional args |
| `./run.sh lint` | Run Ruff linter |
| `./run.sh format` | Run Ruff formatter |
| `./run.sh frontend-check` | TypeScript + lint + build |
| `./run.sh check` | Run all checks (frontend + backend) |
| `./run.sh db-migrate MSG` | Create new Alembic migration |
| `./run.sh db-upgrade` | Run pending migrations |
| `./run.sh db-history` | Show migration history |
| `./run.sh kb-seed` | Seed reference data (vendors, catalog, policies) |
| `./run.sh kb-ingest` | Embed knowledge PDFs into LanceDB |
| `./run.sh kb-init` | Run seed + ingest together |

## CI/CD

POMS uses GitHub Actions with a strict split between **Continuous Integration** (runs on every push and PR to `main`) and **Continuous Deployment** (runs only on version tags). Security scanning runs alongside CI and on a weekly schedule.

### Pipeline overview

```
               Pull request / push to main                      Tag  v*
                             │                                      │
           ┌─────────────────┼──────────────────┐                   │
           ▼                 ▼                  ▼                   ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌──────────────────┐
    │backend.yml │    │frontend.yml│    │ codeql.yml │    │deploy-backend.yml│
    │            │    │            │    │            │    │                  │
    │ • ruff     │    │ • eslint   │    │ • python   │    │ • docker buildx  │
    │ • pytest   │    │ • tsc+vite │    │ • ts / js  │    │ • push to ACR    │
    │   +cov     │    │            │    │ + weekly   │    │ • containerapp   │
    │            │    │            │    │   cron     │    │   update         │
    │ path:      │    │ path:      │    │            │    │ • /health probe  │
    │ src/backend│    │src/frontend│    │            │    └──────────────────┘
    └────────────┘    └────────────┘    └────────────┘    ┌──────────────────┐
                                                          │deploy-frontend   │
                                                          │   .yml           │
                                                          │ • pnpm build     │
                                                          │ • SWA deploy     │
                                                          └──────────────────┘
```

### Continuous Integration

**`backend.yml`** runs two jobs, both path-filtered to `src/backend/**`:

- **Lint & Format** — `uv sync --frozen`, then `ruff check .` and `ruff format --check .`. Zero tolerance for style drift.
- **Tests** — spins up a PostgreSQL 18 service container, creates the `poms_test` database, and runs `pytest --cov=.` against it. Real Postgres, not mocks, because the migrations, async session handling, and JSONB columns need a real database. LLM calls are mocked; tests never hit Azure OpenAI.

**`frontend.yml`** also runs two jobs, path-filtered to `src/frontend/**`:

- **Lint** — `pnpm install --frozen-lockfile` + `pnpm lint` (ESLint v10).
- **Typecheck & Build** — `pnpm build` = `tsc -b && vite build`. Any type error or build failure blocks the merge.

**`codeql.yml`** runs GitHub's default CodeQL Advanced scan for Python and TypeScript/JavaScript (`build-mode: none`) on every push and PR to `main`, plus a weekly cron at `39 1 * * 1`. Results surface in the repo's Security tab.

### Continuous Deployment

Deploys are **tag-driven** — pushes to `main` only run CI, they do **not** deploy. This is deliberate:

- `main` is always deployable but not always deployed — half-done feature merges don't ship.
- Git tags give a human-readable release history and a natural rollback target.
- Rollbacks are a one-liner: repoint the Container App at a previous tag's image.
- `workflow_dispatch` still allows manual releases for hotfixes.

```
    ┌───────────┐
    │ Developer │
    └─────┬─────┘
          │ git tag v0.1.0 && git push --tags
          ▼
    ┌──────────────────────────────────┐
    │       GitHub Actions             │
    │  ─────────────────────────────   │
    │  .github/workflows/              │
    │    deploy-backend.yml            │
    │    deploy-frontend.yml           │
    └────────────────┬─────────────────┘
                     │ OIDC federated login
                     │ (Entra ID app · no long-lived secrets)
                     ▼
    ╔═══════════════════════════════════════════════════════╗
    ║           Azure  ·  rg-poms-demo                      ║
    ║                                                       ║
    ║   ┌──────────────────┐      docker push               ║
    ║   │ Container        │◀─────────── deploy-backend     ║
    ║   │ Registry (Basic) │                                ║
    ║   └────────┬─────────┘                                ║
    ║            │ image pull                               ║
    ║            │ (AcrPull via user-assigned identity)     ║
    ║            ▼                                          ║
    ║   ┌──────────────────┐                                ║
    ║   │ Container App    │   az containerapp update       ║
    ║   │ (new revision)   │◀──────────── deploy-backend    ║
    ║   └──────────────────┘                                ║
    ║                                                       ║
    ║   ┌──────────────────┐   SWA deploy token             ║
    ║   │ Static Web App   │◀──────────── deploy-frontend   ║
    ║   │ (Free tier)      │                                ║
    ║   └──────────────────┘                                ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
```

**`deploy-backend.yml`** logs in via OIDC, builds the backend image with a GitHub Actions layer cache (`cache-from/to: type=gha`), pushes it to ACR tagged with both the version and `:latest`, runs `az containerapp update --image …` to roll a new revision, then curls `/health` on the public FQDN with 6 retries and fails the run if the new revision isn't serving within ~60 seconds.

**`deploy-frontend.yml`** sets up pnpm 9 and Node 22 with lockfile cache, runs `pnpm build` with `VITE_API_BASE_URL=https://<container-app-fqdn>` baked in at build time, and hands `dist/` to `Azure/static-web-apps-deploy@v1` using the SWA deploy token (`skip_app_build: true` because we already built).

#### OIDC authentication to Azure

Neither deploy workflow stores a service principal secret. `src/infra/bootstrap.sh` creates an Entra ID app registration with two **federated credentials** scoped to this repo:

- `repo:<owner>/<name>:ref:refs/heads/main`
- `repo:<owner>/<name>:environment:production`

At deploy time, `azure/login@v2` exchanges the GitHub-issued OIDC token for a short-lived Azure access token. Nothing long-lived lives in GitHub.

### Releasing

After the first-time bootstrap has run, cutting a release is three commands:

```bash
git checkout main && git pull
git tag v0.1.0
git push origin v0.1.0
# → deploy-backend.yml and deploy-frontend.yml run in parallel
```

Both workflows also support manual invocation via `workflow_dispatch` from the Actions tab.

To roll back, point the Container App at a previous tag's image:

```bash
az containerapp update \
  --name ca-poms-backend \
  --resource-group rg-poms-demo \
  --image <registry>.azurecr.io/poms-backend:<previous-version>
```

### Required GitHub Actions secrets

All seeded automatically by `src/infra/bootstrap.sh`:

| Secret | Used by | What it is |
|---|---|---|
| `AZURE_CLIENT_ID` | both deploy workflows | Entra ID app (client) ID |
| `AZURE_TENANT_ID` | both deploy workflows | Entra ID tenant ID |
| `AZURE_SUBSCRIPTION_ID` | both deploy workflows | Target subscription |
| `AZURE_RESOURCE_GROUP` | deploy-backend | Resource group name |
| `AZURE_CONTAINER_REGISTRY` | deploy-backend | ACR login server |
| `AZURE_CONTAINER_APP` | deploy-backend | Container App name |
| `AZURE_CONTAINER_APP_FQDN` | deploy-frontend | Baked into `VITE_API_BASE_URL` |
| `AZURE_STATIC_WEB_APP_TOKEN` | deploy-frontend | SWA deploy API token |

## Deployment (Azure)

POMS ships with Infrastructure-as-Code (Bicep) that targets **Azure Container Apps** for the backend and **Azure Static Web Apps** for the frontend. All infrastructure files live in `src/infra/`. The release workflows that build and ship images are described in the [CI/CD](#cicd) section above.

### Runtime architecture

```
                             ┌───────────┐
                             │   Users   │
                             └─────┬─────┘
                                   │ HTTPS
                                   ▼
         ┌──────────────────────────────────────────────┐
         │  Azure Static Web App  (Free tier)           │
         │  React + TypeScript + Vite                   │
         │  swa-poms-demo                               │
         └──────────────────┬───────────────────────────┘
                            │ fetch  /api/*   (CORS)
                            ▼
         ┌──────────────────────────────────────────────┐
         │  Container Apps Environment                  │
         │  cae-poms-demo                               │
         │                                              │
         │  ┌────────────────────────────────────────┐  │
         │  │  ca-poms-backend                       │  │
         │  │  FastAPI  +  Gmail poller              │  │
         │  │  0.5 vCPU · 1 GiB · min=1 replica      │  │
         │  │                                        │  │
         │  │  volume: /app/data                     │  │
         │  └──┬───────┬──────────┬──────────┬──────┘  │
         └─────┼───────┼──────────┼──────────┼─────────┘
               │       │          │          │
               │       │          │          └──▶ Log Analytics
               │       │          │                (container stdout)
               │       │          │
               │       │          └──▶ Azure Files share
               │       │                (LanceDB vectors)
               │       │
               │       └──▶ Azure OpenAI
               │            • gpt-4o-mini       (completion)
               │            • text-embedding-3-large (embeddings)
               │
               └──▶ PostgreSQL Flexible Server  (Burstable B1ms)
                    database: poms
```

### What gets provisioned

A single Bicep template at `src/infra/main.bicep` declares every Azure resource:

| Resource | Purpose |
|---|---|
| Log Analytics workspace | Observability sink for Container Apps |
| Azure Container Registry (Basic) | Hosts the backend image |
| User-assigned managed identity | Grants `AcrPull` on the registry to the Container App |
| Storage account + Azure Files share | Persists the LanceDB vector store across restarts |
| Container Apps managed environment | Runtime with the file share mounted |
| Container App (`ca-poms-backend`) | FastAPI + Gmail poller, single container, `min=1` replica |
| PostgreSQL Flexible Server (B1ms) | Application database |
| Azure OpenAI account | `gpt-4o-mini` + `text-embedding-3-large` deployments |
| Static Web App (Free) | React frontend |

### First-time deploy

```bash
./src/infra/bootstrap.sh
```

The script:

1. Registers the required resource providers.
2. Creates the resource group (`rg-poms-demo` in North Europe by default).
3. Deploys `main.bicep` with a hello-world placeholder image so the Container App can be created before CI has ever built the real image.
4. Configures GitHub OIDC — app registration + two federated credentials (`refs/heads/main` and `environment:production`).
5. Assigns `Contributor` on the resource group and `AcrPush` on the ACR to the service principal.
6. Fetches the Static Web App deploy token and seeds **8 GitHub Actions secrets** used by the deploy workflows.

See [`src/infra/README.md`](src/infra/README.md) for prerequisites, env var overrides, how to seed the RAG vector store inside the Container App, and teardown commands. The release flow (tag-driven, how to roll back) lives in the [CI/CD](#cicd) section above.

## DISCLAIMER

POMS is a demonstration/portfolio project.
