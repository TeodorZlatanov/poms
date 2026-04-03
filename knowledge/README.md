# Knowledge Base

This directory contains the RAG (Retrieval-Augmented Generation) documents used by the POMS validation pipeline. These files are embedded into LanceDB at startup and queried during purchase order validation.

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

## How it's used

At backend startup, these files are loaded and embedded into a LanceDB vector store. During PO validation, the agent queries the knowledge base using hybrid search (vector similarity + full-text keyword matching) to validate extracted PO data against the company's internal records and policies.
