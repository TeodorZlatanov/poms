# POMS - Purchase Order Management System

AI-powered purchase order processing pipeline. Receives PO emails, extracts structured data via LLM, validates against a RAG knowledge base, and routes based on the resulting issue tags - auto-approving clean POs, flagging soft issues for human review, and never auto-rejecting.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Why RAG Matters](#why-rag-matters)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Project Setup](#project-setup)
- [Running the Application](#running-the-application)
- [Sample PO Files](#sample-po-files)
- [End-to-End Testing](#end-to-end-testing)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [CLI Reference (run.sh)](#cli-reference-runsh)
- [Disclaimer](#disclaimer)

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

## DISCLAIMER

POMS is a demonstration/portfolio project.
