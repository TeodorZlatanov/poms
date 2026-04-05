# Knowledge Base

This directory contains the source data for the POMS validation pipeline. The files serve two purposes:

1. **Database seeding** - `vendors.json` and `catalog.json` are loaded into PostgreSQL reference tables via `scripts/seed_reference_data.py` for deterministic validation.
2. **RAG ingestion** - `generate_pdfs.py` produces rich PDFs in `pdfs/` that are embedded into LanceDB via `scripts/ingest_knowledge.py` for AI-powered validation.

## Files

### vendors.json

Approved vendor registry. Contains 10 vendors with:
- Vendor ID, name, contact email
- Contract status (active/expired) and expiry date
- Address and payment terms

Used for: vendor validation, fuzzy name matching, contract status checks.

### catalog.json

Product catalog with 15 items. Each product has:
- SKU, description, category
- Unit price (EUR), unit of measure
- Minimum order quantity

Used for: price validation (flags >10% deviation), product/SKU recognition.

### policies.md

Corporate procurement policy document (12 sections) covering:
- Department spending limits
- Maximum payment terms (Net 30)
- Approval thresholds by order value
- Required fields for PO submission
- Allowed currencies
- Vendor requirements
- Pricing compliance rules

Used for: policy compliance checks, spending limit validation, payment terms validation, completeness checks.

### pdfs/

Generated PDFs containing enriched knowledge base content (vendor profiles with framework agreements, Q4 surcharges, grace periods, etc.). These go beyond the raw JSON/MD data to include nuanced business context that the RAG agent uses to make smarter validation decisions.

Regenerate with: `cd knowledge && python generate_pdfs.py`

## How it works

### Step 1: Seed reference data (deterministic validation)

```bash
cd backend && uv run python -m scripts.seed_reference_data
```

Loads `vendors.json` and `catalog.json` into PostgreSQL tables (`approved_vendors`, `product_catalog`, `procurement_policies`). These are used for exact vendor matching, price comparison, and spending limit checks.

### Step 2: Ingest PDFs into LanceDB (RAG validation)

```bash
cd backend && uv run python -m scripts.ingest_knowledge
```

Processes PDFs in `pdfs/` through PyMuPDF, splits by markdown headers, embeds with Azure OpenAI, and stores in LanceDB with hybrid search (vector + full-text). At startup, the backend connects to the existing LanceDB table - it does not re-embed.
