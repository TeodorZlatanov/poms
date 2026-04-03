import json
from pathlib import Path

import lancedb
from loguru import logger

from core.config import settings

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"


class KnowledgeBase:
    def __init__(self):
        self.db: lancedb.DBConnection | None = None
        self._vendors_data: list[dict] = []
        self._catalog_data: list[dict] = []
        self._policies_sections: list[dict] = []

    async def initialize(self):
        """Connect to LanceDB and seed tables from knowledge/ files."""
        self.db = await lancedb.connect_async(settings.lancedb_path)
        self._load_raw_data()
        await self._seed_tables()
        logger.info(
            "Knowledge base initialized with {} vendors, {} products, {} policy sections",
            len(self._vendors_data),
            len(self._catalog_data),
            len(self._policies_sections),
        )

    def _load_raw_data(self):
        """Load raw JSON/MD files into memory for direct lookups."""
        vendors_path = KNOWLEDGE_DIR / "vendors.json"
        with open(vendors_path) as f:
            self._vendors_data = json.load(f)["approved_vendors"]

        catalog_path = KNOWLEDGE_DIR / "catalog.json"
        with open(catalog_path) as f:
            self._catalog_data = json.load(f)["products"]

        policies_path = KNOWLEDGE_DIR / "policies.md"
        policies_text = policies_path.read_text()
        # Split by ## section headings
        sections = []
        current_title = ""
        current_body = ""
        for line in policies_text.split("\n"):
            if line.startswith("## "):
                if current_title:
                    sections.append({"title": current_title, "text": current_body.strip()})
                current_title = line.lstrip("# ").strip()
                current_body = ""
            else:
                current_body += line + "\n"
        if current_title:
            sections.append({"title": current_title, "text": current_body.strip()})
        self._policies_sections = sections

    async def _seed_tables(self):
        """Seed LanceDB tables if they don't already exist."""
        existing = await self.db.table_names()

        if "vendors" not in existing:
            rows = []
            for v in self._vendors_data:
                text = (
                    f"Vendor: {v['name']} | Status: {v['contract_status']} | "
                    f"Terms: {v['payment_terms']} | "
                    f"City: {v['address']['city']}, {v['address']['country']}"
                )
                rows.append(
                    {
                        "text": text,
                        "name": v["name"],
                        "vendor_id": v["id"],
                        "contract_status": v["contract_status"],
                        "contract_expiry_date": v.get("contract_expiry_date", ""),
                        "payment_terms": v["payment_terms"],
                    }
                )
            await self.db.create_table("vendors", data=rows)
            logger.info("Seeded vendors table with {} rows", len(rows))

        if "catalog" not in existing:
            rows = []
            for p in self._catalog_data:
                text = (
                    f"SKU: {p['sku']} | {p['description']} | "
                    f"Price: {p['unit_price']} {p['currency']} | "
                    f"Category: {p['category']}"
                )
                rows.append(
                    {
                        "text": text,
                        "sku": p["sku"],
                        "description": p["description"],
                        "unit_price": p["unit_price"],
                        "currency": p["currency"],
                        "category": p["category"],
                        "min_order_quantity": p["min_order_quantity"],
                    }
                )
            await self.db.create_table("catalog", data=rows)
            logger.info("Seeded catalog table with {} rows", len(rows))

        if "policies" not in existing:
            rows = [{"text": s["text"], "title": s["title"]} for s in self._policies_sections]
            await self.db.create_table("policies", data=rows)
            logger.info("Seeded policies table with {} rows", len(rows))

    def lookup_vendor(self, name: str) -> dict | None:
        """Exact case-insensitive vendor lookup from in-memory data."""
        name_lower = name.lower().strip()
        for v in self._vendors_data:
            if v["name"].lower().strip() == name_lower:
                return v
        return None

    def fuzzy_match_vendor(self, name: str, threshold: float = 0.6) -> dict | None:
        """Simple fuzzy vendor match using token overlap ratio."""
        name_tokens = set(name.lower().split())
        best_match = None
        best_score = 0.0
        for v in self._vendors_data:
            vendor_tokens = set(v["name"].lower().split())
            if not name_tokens or not vendor_tokens:
                continue
            overlap = len(name_tokens & vendor_tokens)
            total = len(name_tokens | vendor_tokens)
            score = overlap / total if total > 0 else 0.0
            if score > best_score:
                best_score = score
                best_match = v
        if best_score >= threshold:
            return best_match
        return None

    def lookup_product_by_sku(self, sku: str) -> dict | None:
        """Exact SKU lookup from in-memory catalog data."""
        sku_upper = sku.upper().strip()
        for p in self._catalog_data:
            if p["sku"].upper().strip() == sku_upper:
                return p
        return None

    def get_department_limit(self, department: str) -> float | None:
        """Get the per-order spending limit for a department."""
        limits = {
            "engineering": 5000.0,
            "marketing": 5000.0,
            "operations": 10000.0,
            "finance": 15000.0,
            "hr": 3000.0,
        }
        return limits.get(department.lower().strip()) if department else None


# Singleton instance
knowledge_base = KnowledgeBase()
