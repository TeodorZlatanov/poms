# POMS — Purchase Order Management System

AI-powered purchase order processing pipeline. Receives PO emails, extracts structured data via LLM, validates against a RAG knowledge base (vendors, pricing, policies), and routes based on the resulting issue tags. Auto-approves clean POs, flags soft issues for human review, never auto-rejects.

## Tech Stack

**Backend:** Python 3.13+ · FastAPI (async only) · Agno (agent framework) · Azure OpenAI (LLM + embeddings) · LanceDB (vector store, hybrid search) · SQLModel + asyncpg (PostgreSQL ORM) · Alembic (migrations, auto-run on startup) · Gmail API (OAuth2) · PyMuPDF · pandas · Loguru
**Frontend:** React 19 · TypeScript (strict) · Vite · TanStack Query · Tailwind CSS 4
**Infrastructure:** PostgreSQL 18 · Docker Compose · uv (Python) · pnpm (frontend) · Ruff (lint/format)

## Commands

```bash
# Backend
cd backend && uv run fastapi dev main.py        # Dev server with hot reload
cd backend && uv run ruff check .                # Lint
cd backend && uv run ruff format .               # Format
cd backend && uv run pytest                      # Run tests
cd backend && uv run pytest -v --cov=backend     # Tests with coverage
cd backend && uv run alembic revision --autogenerate -m "description"  # New migration

# Frontend
cd frontend && pnpm dev                          # Dev server
cd frontend && pnpm build                        # Production build
cd frontend && pnpm lint                         # Lint

# Infrastructure
docker compose up -d                             # Start PostgreSQL
docker compose down                              # Stop services

# CLI (run.sh wraps common commands)
./run.sh                                         # See available commands
```

## Project Structure

```
poms/
├── backend/
│   ├── api/routes/          # HTTP endpoints (orders, reviews, webhook, analytics)
│   ├── agent/               # AI pipeline (classifier, extractor, validator, router, prompts)
│   ├── core/                # Config (BaseSettings), database engine, Loguru setup
│   ├── models/              # SQLModel database models + enums
│   ├── schemas/             # Pydantic request/response schemas (separate from DB models)
│   ├── services/            # Business logic (email, pipeline, poller, files, knowledge)
│   ├── migrations/          # Alembic migrations (auto-run on startup via lifespan)
│   ├── tests/               # pytest tests mirroring backend structure
│   └── main.py              # FastAPI app entry point
├── frontend/src/
│   ├── api/                 # API client (fetch wrapper + types)
│   ├── components/          # UI components (orders/, reviews/, analytics/, layout/)
│   ├── hooks/               # TanStack Query hooks (useOrders, useReviewAction, etc.)
│   ├── pages/               # Route pages (dashboard, order detail, analytics)
│   └── types/               # Shared TypeScript interfaces
├── knowledge/               # RAG documents: vendors.json, catalog.json, policies.md
├── samples/                 # Mock PO files for demo (9 samples: 3 scenarios × PDF/XLSX/PNG)
└── docker-compose.yml       # PostgreSQL 18
```

## Architecture

Pipeline architecture: both entry points (Gmail poller, webhook) normalize to the same format and feed the same pipeline.

```
Email → Classify (is PO?) → Extract (LLM → JSON) → Validate (RAG) → Route → Act
```

**Routing rules:**
- No issue tags → AUTO-APPROVED (store + confirmation email)
- Soft tags only → FLAGGED FOR REVIEW (store + ack email + dashboard queue)
- Any hard tags → REJECTED pending human confirmation (store + ack email + urgent flag)

**Key principle:** The agent auto-approves but NEVER auto-rejects.

## API Endpoints

```
POST /api/webhook/email          # Ingest email payload → triggers pipeline (202)
GET  /api/orders                 # List POs (filterable by status, date, vendor)
GET  /api/orders/{id}            # PO detail with validations, tags, emails, logs
POST /api/reviews/{order_id}     # Submit review decision (approve/reject + comment)
GET  /api/analytics              # Dashboard analytics (volume, rates, common tags)
```

## Database

6 tables, all with UUID PKs and created_at/updated_at timestamps:

- `purchase_orders` — PO data + status + line_items (JSONB) + batch_id
- `validation_checks` — Per-check results (vendor/price/policy/completeness/rag)
- `issue_tags` — Tag name + severity (soft/hard)
- `review_decisions` — Reviewer decision + comment
- `processing_logs` — Step name + duration_ms + metadata (JSONB)
- `email_logs` — Direction + type + sender/recipient

Enums stored as VARCHAR, validated in Python. Migrations auto-run on startup. Never write manual SQL for schema changes.

## Issue Tags

| Tag | Severity | Trigger |
|-----|----------|---------|
| `UNKNOWN_VENDOR` | Hard | Not in vendor registry |
| `EXPIRED_CONTRACT` | Hard | Vendor contract expired |
| `OVER_LIMIT` | Hard | Exceeds department spending limit |
| `TERMS_VIOLATION` | Soft/Hard | Payment terms outside policy |
| `MISSING_FIELD` | Soft/Hard | Required field absent |
| `VENDOR_FUZZY_MATCH` | Soft | Close but not exact vendor name |
| `PRICE_MISMATCH` | Soft | Unit price >10% from catalog |
| `UNKNOWN_PRODUCT` | Soft | SKU not in product catalog |

## Coding Conventions

### Python

- Async everywhere — no blocking I/O in the event loop
- Type hints on all function signatures, `str | None` syntax (not `Optional`)
- Pydantic models at all boundaries — no raw dicts crossing modules
- Thin routes, thick services — routes dispatch, `services/` and `agent/` contain logic
- Custom exception classes for domain errors, FastAPI exception handlers for HTTP conversion
- No wildcard imports
- Dependency injection via `Depends()` — sessions, services, config
- Structured logging with Loguru `bind()` — every log includes correlation ID
- Ruff: zero warnings, configured in `pyproject.toml`

### TypeScript / React

- `strict: true`, no `any`, no `@ts-ignore`
- Functional components only
- TanStack Query for all server state — no `useEffect` + `useState` for data fetching
- Components render, hooks contain logic
- Named exports (except page components)
- Tailwind utility classes only — no custom CSS files
- Always handle loading, error, and empty states

### Database

- Schema changes only through Alembic migrations
- UUIDs for primary keys, timestamps on every table
- Foreign keys with explicit CASCADE/RESTRICT rules
- JSONB for variable structures (line_items, validation details)
- Enums in Python code, stored as VARCHAR
- Indexes on: `status`, `order_id` (child tables), `created_at`
- Async sessions only, scoped to request lifecycle

## Testing

```bash
uv run pytest                                    # All tests
uv run pytest tests/agent/test_router.py         # Specific file
uv run pytest -k "test_routing"                  # Pattern match
```

- pytest + pytest-asyncio (`asyncio_mode = "auto"`)
- httpx `AsyncClient` with `ASGITransport` for API tests
- Separate `poms_test` database, per-test transaction rollback
- Mock all LLM calls — tests never hit Azure OpenAI API
- Test routing logic, tag generation, completeness, endpoints, file parsing, edge cases
- Do NOT test: LLM output quality, Gmail connectivity, frontend, migration correctness

## Naming Conventions

- **Files/folders:** lowercase, underscores only when two words are essential
- **Python:** snake_case everywhere
- **TypeScript files:** camelCase; components: PascalCase
- **Database tables:** snake_case, plural (`purchase_orders`, `issue_tags`)
- **API routes:** kebab-case (`/api/webhook/email`)
- **Environment variables:** UPPER_SNAKE_CASE

## Key References

- Full PRD: `.claude/PRD.md`
- Task planning: `PROJECT-TASK.md`
- Knowledge base docs: `knowledge/`
- Sample PO files: `samples/`
