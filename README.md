# POMS — Purchase Order Management System

AI-powered purchase order processing pipeline. Receives PO emails, extracts structured data via LLM, validates against a RAG knowledge base, and routes based on confidence — auto-approving clean POs, flagging uncertain ones for human review, and never auto-rejecting.

## Overview

POMS automates procurement document processing through a multi-stage AI pipeline:

1. **Classify** — Determine if an incoming email contains a purchase order
2. **Extract** — Use an LLM to parse PO data into structured JSON (vendor, line items, amounts, terms)
3. **Validate** — Cross-reference extracted data against a RAG knowledge base (vendor registry, product catalog, company policies)
4. **Route** — Based on validation results, auto-approve, flag for review, or mark for rejection
5. **Act** — Persist the order, send confirmation/notification emails, and surface in the dashboard

The system combines AI extraction with human oversight: clean POs flow through automatically, while edge cases surface in a review dashboard with full context.

## Architecture

```
Email/Webhook → Classify → Extract (LLM) → Validate (RAG) → Route → Persist + Notify
                                                                         ↓
                                                              Dashboard (React)
```

**Routing rules:**
- No issues → **Auto-approved** (stored + confirmation email)
- Soft issues only → **Flagged for review** (dashboard queue + ack email)
- Any hard issues → **Rejected** pending human confirmation (urgent flag)

**Key principle:** The system auto-approves but never auto-rejects.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13+, FastAPI, async everywhere |
| AI/LLM | Agno (agent framework), Anthropic Claude |
| RAG | LanceDB (vector store, hybrid search) |
| Database | PostgreSQL 18, SQLModel + asyncpg, Alembic |
| Email | Gmail API (OAuth2) |
| Frontend | React 19, TypeScript (strict), Vite, TanStack Query, Tailwind CSS 4 |
| Infrastructure | Docker Compose, uv (Python), pnpm (frontend), Ruff (lint/format) |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.13+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) (frontend package manager)

### Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd poms

# Start PostgreSQL
docker compose up -d

# Install backend dependencies
cd backend && uv sync && cd ..

# Install frontend dependencies
cd frontend && pnpm install && cd ..
```

### Configure Environment

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=postgresql+asyncpg://poms:poms@localhost:5432/poms
ANTHROPIC_API_KEY=your-api-key-here
```

### Run

```bash
# Terminal 1: Backend
cd backend && uv run fastapi dev main.py

# Terminal 2: Frontend
cd frontend && pnpm dev
```

Open http://localhost:3000 to access the dashboard.

## Demo

Test the full pipeline by submitting sample POs via the webhook endpoint:

```bash
# Submit a clean PO (auto-approved)
curl -X POST http://localhost:8000/api/webhook/email \
  -H "Content-Type: application/json" \
  -d '{
    "from": "purchasing@acme.com",
    "subject": "PO-2024-0047",
    "body": "Please process the attached purchase order.",
    "attachments": [{
      "filename": "po_clean.pdf",
      "content_type": "application/pdf",
      "data": "<base64-encoded-pdf>"
    }],
    "received_at": "2024-11-15T10:30:00Z"
  }'
```

Three sample PO files are included in `samples/`:

| File | Expected Result | Why |
|------|----------------|-----|
| `po_clean.pdf` | Auto-approved | Known vendor, valid prices, all fields present |
| `po_fuzzy.pdf` | Flagged for review | Vendor name close but not exact match, minor price discrepancies |
| `po_bad.pdf` | Rejected (pending review) | Unknown vendor, missing fields, policy violations |

After submission, view results in the dashboard:
- **Orders page** — See PO status, click through to detail view
- **Order detail** — View extracted data, validation results, issue tags, processing timeline
- **Review panel** — Approve or reject flagged POs with optional comments
- **Analytics** — See processing volume, approval rates, common issue tags

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/webhook/email` | Ingest email payload, triggers pipeline (202) |
| `GET` | `/api/orders/` | List POs (filter by status, vendor; paginated) |
| `GET` | `/api/orders/{id}` | PO detail with validations, tags, emails, logs |
| `POST` | `/api/reviews/{order_id}` | Submit review decision (approve/reject + comment) |
| `GET` | `/api/analytics/` | Dashboard analytics (volume, rates, common tags) |

## Project Structure

```
poms/
├── backend/
│   ├── api/routes/          # HTTP endpoints
│   ├── agent/               # AI pipeline stages + prompts
│   ├── core/                # Config, database, logging
│   ├── models/              # SQLModel database models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic (email, pipeline, poller)
│   ├── migrations/          # Alembic (auto-run on startup)
│   └── tests/               # pytest test suite
├── frontend/src/
│   ├── api/                 # API client + endpoint functions
│   ├── components/          # UI components (orders, reviews, analytics, layout)
│   ├── hooks/               # TanStack Query hooks
│   ├── pages/               # Route pages (dashboard, order detail, analytics)
│   └── types/               # TypeScript interfaces
├── knowledge/               # RAG documents (vendors, catalog, policies)
├── samples/                 # Sample PO files for testing
└── docker-compose.yml       # PostgreSQL + pgAdmin
```

## Testing

```bash
# Run backend tests
cd backend && uv run pytest -v

# Run with coverage
cd backend && uv run pytest -v --cov=backend

# Frontend type checking
cd frontend && npx tsc --noEmit

# Frontend lint
cd frontend && pnpm lint

# Frontend production build
cd frontend && pnpm build
```

## Production Notes

This is a demonstration/portfolio project. For production deployment, consider:

- **Authentication** — Add user auth (OAuth2/OIDC) for the dashboard and API
- **HTTPS** — TLS termination via reverse proxy (nginx, Caddy)
- **Rate limiting** — Protect the webhook endpoint from abuse
- **Secrets management** — Use a vault or cloud secret manager instead of `.env` files
- **Monitoring** — APM, error tracking (Sentry), structured log aggregation
- **Email reliability** — Queue-based email sending with retries
- **Horizontal scaling** — Stateless backend behind a load balancer, shared PostgreSQL
- **File storage** — S3/GCS for PO attachments instead of local processing
- **CI/CD** — Automated testing, linting, and deployment pipeline
