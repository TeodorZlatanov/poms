"""Generate rich knowledge base PDFs for RAG ingestion.

These PDFs contain nuanced business context that goes beyond what deterministic
DB checks can handle — policy exceptions, volume discounts, vendor relationships,
framework agreements, grace periods, etc. This is where RAG adds real value.

Usage: cd knowledge && python generate_pdfs.py
"""

import pymupdf

FONT_SIZE_TITLE = 18
FONT_SIZE_H1 = 14
FONT_SIZE_H2 = 12
FONT_SIZE_BODY = 10
FONT_SIZE_SMALL = 9
LINE_HEIGHT = 14
MARGIN_LEFT = 50
MARGIN_TOP = 60
PAGE_WIDTH = 595  # A4
PAGE_HEIGHT = 842  # A4
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN_LEFT


def _add_page(doc: pymupdf.Document) -> pymupdf.Page:
    return doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)


def _write_text(
    page: pymupdf.Page,
    y: float,
    text: str,
    fontsize: float = FONT_SIZE_BODY,
    bold: bool = False,
    indent: float = 0,
) -> float:
    """Write text at position, handling line wrapping. Returns new y position."""
    font = "helv" if not bold else "hebo"
    x = MARGIN_LEFT + indent
    width = TEXT_WIDTH - indent

    # Split into lines and wrap
    for line in text.split("\n"):
        if not line.strip():
            y += fontsize * 0.8
            continue

        # Simple word wrapping
        words = line.split()
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            text_length = pymupdf.get_text_length(test_line, fontname=font, fontsize=fontsize)
            if text_length > width and current_line:
                if y > PAGE_HEIGHT - 60:
                    return y  # Signal need for new page
                page.insert_text(
                    (x, y), current_line, fontname=font, fontsize=fontsize, color=(0, 0, 0)
                )
                y += fontsize * 1.4
                current_line = word
            else:
                current_line = test_line
        if current_line:
            if y > PAGE_HEIGHT - 60:
                return y
            page.insert_text(
                (x, y), current_line, fontname=font, fontsize=fontsize, color=(0, 0, 0)
            )
            y += fontsize * 1.4

    return y


def _write_section(doc: pymupdf.Document, page: pymupdf.Page, y: float, title: str, body: str) -> tuple[pymupdf.Page, float]:
    """Write a section with title and body, creating new pages as needed."""
    # Check if we need a new page for the title
    if y > PAGE_HEIGHT - 120:
        page = _add_page(doc)
        y = MARGIN_TOP

    # Title
    y += 8
    page.insert_text(
        (MARGIN_LEFT, y), title, fontname="hebo", fontsize=FONT_SIZE_H2, color=(0.15, 0.15, 0.4)
    )
    y += FONT_SIZE_H2 * 1.6

    # Body paragraphs
    for paragraph in body.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Check for bullet points
        lines = paragraph.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_bullet = line.startswith("- ") or line.startswith("* ")
            indent = 15 if is_bullet else 0
            bold = line.startswith("**") and line.endswith("**")
            if bold:
                line = line.strip("*")

            new_y = _write_text(page, y, line, fontsize=FONT_SIZE_BODY, bold=bold, indent=indent)
            if new_y > PAGE_HEIGHT - 60:
                page = _add_page(doc)
                y = MARGIN_TOP
                y = _write_text(page, y, line, fontsize=FONT_SIZE_BODY, bold=bold, indent=indent)
            else:
                y = new_y

        y += 4  # Paragraph spacing

    return page, y


def _write_title_page(doc: pymupdf.Document, title: str, subtitle: str, doc_id: str, effective_date: str) -> None:
    """Write a title page."""
    page = _add_page(doc)
    y = 250
    page.insert_text(
        (MARGIN_LEFT, y), title, fontname="hebo", fontsize=FONT_SIZE_TITLE, color=(0.1, 0.1, 0.35)
    )
    y += 30
    page.insert_text(
        (MARGIN_LEFT, y), subtitle, fontname="helv", fontsize=FONT_SIZE_H2, color=(0.3, 0.3, 0.3)
    )
    y += 50
    for info in [
        f"Document ID: {doc_id}",
        f"Effective Date: {effective_date}",
        "Classification: Internal Use Only",
        "Approved By: Chief Financial Officer",
    ]:
        page.insert_text((MARGIN_LEFT, y), info, fontname="helv", fontsize=FONT_SIZE_BODY, color=(0.4, 0.4, 0.4))
        y += 16


# =============================================================================
# DOCUMENT 1: APPROVED VENDOR REGISTRY
# =============================================================================

VENDOR_SECTIONS = [
    ("1. Overview and Purpose", """This document serves as the authoritative reference for all approved vendors authorized to supply goods and services to the organization. It includes vendor profiles, contract details, known name variations, subsidiary relationships, framework agreements, and escalation procedures.

All purchase orders must reference a vendor listed in this registry with an active contract status. Orders referencing vendors not in this registry, or vendors with expired contracts, require special handling as described in the Policy Exceptions and Grace Periods sections."""),

    ("2. Vendor Profile: TechParts Bulgaria OOD (VND-001)", """**Contract Status: ACTIVE**
**Contract Expiry: 31 March 2027**
**Payment Terms: Net 30**
**Primary Contact: orders@techparts.bg**
**Address: ul. Tsarigradsko Shose 115, 1784 Sofia, Bulgaria**

TechParts Bulgaria OOD is a preferred vendor and the primary supplier of electronic components and sensor modules for the Engineering department. They hold a framework agreement (FA-2024-001) covering all electronics category products with pre-negotiated pricing.

**Known Name Variations:**
- TechParts Bulgaria OOD (official registered name)
- TechParts BG (commonly used abbreviation)
- TP Bulgaria OOD (abbreviated form on some invoices)
- Tech Parts Bulgaria (English transliteration without OOD suffix)

**Framework Agreement FA-2024-001:**
- Covers: All products in the Electronics category (SKU-4421, SKU-3345, and related components)
- Pre-negotiated pricing: Catalog prices are guaranteed for the contract duration
- Volume commitment: Minimum EUR 5,000 annual spend (currently being met)
- Delivery guarantee: 10 business days for standard orders, 5 business days for urgent
- Quality assurance: ISO 9001:2015 certified, all components include test certificates

**Escalation Contacts:**
- Standard orders: orders@techparts.bg
- Urgent/expedited: urgent@techparts.bg (Dimitar Kolev, Account Manager)
- Disputes/quality: quality@techparts.bg

**Vendor Performance Notes:**
- Consistently delivers on time (98.5% on-time delivery rate over last 12 months)
- Zero quality incidents in current contract period
- Recommended for automatic approval on standard orders within catalog pricing"""),

    ("3. Vendor Profile: Acme Corporation Ltd (VND-002)", """**Contract Status: ACTIVE**
**Contract Expiry: 30 June 2027**
**Payment Terms: Net 30**
**Primary Contact: procurement@acmecorp.eu**
**Address: Kurfuerstendamm 42, 10719 Berlin, Germany**

Acme Corporation Ltd is a major European supplier of mechanical components, timing belts, and precision parts. They are the exclusive supplier for HTD-profile timing belts used in production line machinery.

**Known Name Variations:**
- Acme Corporation Ltd (official registered name in UK Companies House)
- Acme Corp (commonly used abbreviation - this is the SAME entity)
- Acme Corp. (with period)
- Acme Corporation (without Ltd suffix)
- Acme GmbH (German subsidiary, same billing entity)
- ACME Corporation Ltd (all-caps variation)

**IMPORTANT:** "Acme Corp" appearing on purchase orders should be treated as a valid reference to "Acme Corporation Ltd" — this is a well-known abbreviation used by the vendor themselves on their quotations and delivery notes. Do not flag as an unknown vendor.

**Volume Discount Schedule (effective from contract renewal 2024-07-01):**
- Standard catalog pricing applies for quantities up to 49 units
- Orders of 50-199 units: 10% discount from catalog price applies
- Orders of 200-499 units: 15% discount from catalog price applies
- Orders of 500+ units: 20% discount from catalog price, requires framework PO

**Example for SKU-7890 (Precision Timing Belt, catalog price EUR 15.00):**
- 1-49 units: EUR 15.00 per unit
- 50-199 units: EUR 13.50 per unit (10% discount)
- 200-499 units: EUR 12.75 per unit (15% discount)
- 500+ units: EUR 12.00 per unit (20% discount)

Note: Prices ABOVE catalog but within the volume discount tier adjustment range should not be flagged as price mismatches. For example, a PO at EUR 17.50 per unit for a small quantity order may reflect shipping surcharges or special packaging requirements that the vendor has communicated separately. Deviations up to 20% above catalog should be reviewed in context, not automatically flagged.

**Seasonal Pricing Adjustments:**
- Q4 orders (October-December): Acme applies a 5% seasonal surcharge on mechanical components due to high demand. This is pre-approved and should not be flagged.
- Q1 orders (January-March): Standard pricing applies.

**Escalation Contacts:**
- Orders: procurement@acmecorp.eu
- Technical support: techsupport@acmecorp.eu
- Account Manager: Hans Mueller (h.mueller@acmecorp.eu)"""),

    ("4. Vendor Profile: Balkan Electronics EOOD (VND-003)", """**Contract Status: ACTIVE**
**Contract Expiry: 31 December 2026**
**Payment Terms: Net 15**
**Primary Contact: sales@balkanelectronics.bg**
**Address: bul. Vitosha 89, 1463 Sofia, Bulgaria**

Balkan Electronics EOOD is a local Bulgarian supplier specializing in electronic components and automation equipment. They offer competitive pricing on locally-stocked items with fast delivery times.

**Known Name Variations:**
- Balkan Electronics EOOD (official registered name)
- Balkan Electronics (without EOOD suffix)
- BE EOOD (abbreviated)

**Special Terms:**
- Fast delivery: Same-day delivery available for orders placed before 10:00 AM for in-stock items
- Payment terms are Net 15 (shorter than standard Net 30) — this is contractually agreed and should not be flagged as unusual
- Minimum order value: EUR 100.00 (higher than company standard of EUR 50.00)"""),

    ("5. Vendor Profile: Nordic Supply Solutions AB (VND-004)", """**Contract Status: ACTIVE**
**Contract Expiry: 15 January 2027**
**Payment Terms: Net 30**
**Primary Contact: orders@nordicsupply.se**
**Address: Sveavagen 28, 111 34 Stockholm, Sweden**

Nordic Supply Solutions AB supplies hydraulic components and safety equipment. They are the preferred vendor for safety-critical components requiring CE certification.

**Known Name Variations:**
- Nordic Supply Solutions AB (official)
- Nordic Supply (common abbreviation)
- NSS AB (internal abbreviation used by Engineering)

**Compliance Notes:**
- All safety equipment from Nordic Supply includes CE certification documentation
- Safety-critical components (Safety Light Curtains, Emergency Stop units) require quality verification on receipt
- Nordic Supply has agreed to accept returns within 30 days for safety equipment that fails incoming inspection"""),

    ("6. Vendor Profile: Plovdiv Industrial Supply AD (VND-005)", """**Contract Status: ACTIVE**
**Contract Expiry: 30 September 2026**
**Payment Terms: Net 15**
**Primary Contact: info@plovdivindustrial.bg**
**Address: ul. Gladstone 18, 4000 Plovdiv, Bulgaria**

Plovdiv Industrial Supply AD provides infrastructure materials including cable trays, busbars, and general industrial supplies.

**Known Name Variations:**
- Plovdiv Industrial Supply AD (official)
- Plovdiv Industrial (common abbreviation)
- PIS AD (internal abbreviation)

**Regional Delivery Notes:**
- Free delivery for orders over EUR 500 within Bulgaria
- Orders to Sofia warehouse: next business day
- Orders to regional sites: 2-3 business days"""),

    ("7. Vendor Profile: EuroFasteners GmbH (VND-006)", """**Contract Status: ACTIVE**
**Contract Expiry: 31 August 2027**
**Payment Terms: Net 30**
**Primary Contact: verkauf@eurofasteners.de**
**Address: Industriestrasse 7, 80939 Munich, Germany**

EuroFasteners GmbH is the primary supplier for all fastener products (bolts, nuts, washers, screws). They maintain a consignment stock at our Sofia warehouse.

**Known Name Variations:**
- EuroFasteners GmbH (official)
- Euro Fasteners GmbH (with space)
- EuroFasteners (without GmbH)

**Consignment Stock Agreement:**
- EuroFasteners maintains a consignment stock of standard fasteners (M6-M16 range) at our Sofia warehouse
- Consignment stock is invoiced monthly based on actual consumption
- Purchase orders for consignment items may show EUR 0.00 unit price — this is correct and should not be flagged as a pricing anomaly
- Non-standard fasteners (special materials, non-metric) require standard PO process

**Bulk Pricing:**
- Fastener orders over 5,000 pieces: additional 8% discount from catalog
- Fastener orders over 10,000 pieces: additional 12% discount from catalog"""),

    ("8. Vendor Profile: MediterraneanParts SRL (VND-007)", """**Contract Status: EXPIRED (as of 31 December 2025)**
**Payment Terms: Net 30**
**Primary Contact: ordini@medparts.it**
**Address: Via Roma 156, 20121 Milan, Italy**

MediterraneanParts SRL's contract expired on 31 December 2025. Contract renewal negotiations are currently in progress.

**IMPORTANT — Contract Renewal Grace Period:**
The organization maintains a 90-day grace period policy for vendors whose contracts have expired but are in active renewal negotiations. During this grace period:
- Purchase orders from MediterraneanParts SRL may be processed with a SOFT flag (not hard rejection)
- The grace period extends until 31 March 2026
- Orders during the grace period require department head approval but do not require CFO sign-off
- After the grace period expires, orders from this vendor will be treated as unknown vendor orders

**Renewal Status (as of last update):**
- Renewal negotiations initiated: 15 November 2025
- New contract terms under review by Legal
- Expected completion: Q1 2026
- Contact for renewal status: procurement@company.bg

**Known Name Variations:**
- MediterraneanParts SRL (official)
- Mediterranean Parts (English version)
- MedParts SRL (abbreviated)
- MediterraneanParts S.r.l. (Italian legal format)"""),

    ("9. Vendor Profile: Stara Zagora Metals OOD (VND-008)", """**Contract Status: ACTIVE**
**Contract Expiry: 30 November 2026**
**Payment Terms: Net 15**
**Primary Contact: contact@szmetals.bg**
**Address: ul. Industrialna 34, 6000 Stara Zagora, Bulgaria**

Stara Zagora Metals OOD supplies raw metals, copper busbars, and metal fabrication services.

**Known Name Variations:**
- Stara Zagora Metals OOD (official)
- SZ Metals (common abbreviation)
- Stara Zagora Metals (without OOD)

**Special Pricing Conditions:**
- Metal prices are subject to London Metal Exchange (LME) fluctuations
- Catalog prices are updated quarterly based on LME averages
- Price deviations of up to 15% from catalog are normal for copper and aluminum products and should not be flagged as price mismatches
- For price deviations above 15%, the vendor provides an LME reference with the quotation"""),

    ("10. Vendor Profile: Dutch Logistics BV (VND-009)", """**Contract Status: ACTIVE**
**Contract Expiry: 30 April 2027**
**Payment Terms: Net 30**
**Primary Contact: inkoop@dutchlogistics.nl**
**Address: Herengracht 502, 1017 CB Amsterdam, Netherlands**

Dutch Logistics BV provides logistics services, packaging materials, and warehouse supplies.

**Known Name Variations:**
- Dutch Logistics BV (official)
- Dutch Logistics (without BV)
- DL BV (abbreviated)

**Service Agreements:**
- Logistics services are billed monthly in arrears
- Purchase orders for logistics services may reference service periods rather than specific quantities
- Minimum monthly commitment: EUR 1,500"""),

    ("11. Vendor Profile: Varna Shipyard Components AD (VND-010)", """**Contract Status: ACTIVE**
**Contract Expiry: 28 February 2027**
**Payment Terms: Net 30**
**Primary Contact: parts@varnashipyard.bg**
**Address: ul. Devnya 12, 9000 Varna, Bulgaria**

Varna Shipyard Components AD supplies marine-grade and heavy industrial components.

**Known Name Variations:**
- Varna Shipyard Components AD (official)
- Varna Shipyard (common abbreviation)
- VSC AD (internal abbreviation)

**Special Handling:**
- Marine-grade components require additional quality documentation (Lloyd's Register certification)
- Lead times are typically 4-6 weeks for custom fabrication
- Expedited orders incur a 25% surcharge (pre-approved, should not be flagged)"""),

    ("12. Vendor Onboarding Process for Unknown Vendors", """When a purchase order references a vendor not found in the approved vendor registry, the following process applies:

**Standard Onboarding (10+ business days):**
1. Submit vendor onboarding request to procurement@company.bg
2. Procurement team conducts vendor due diligence (financial stability, references, compliance)
3. Legal team reviews and drafts vendor agreement
4. Finance approves payment terms
5. Vendor is added to the registry with a probationary status for the first 6 months

**Emergency Vendor Onboarding (3-5 business days):**
For urgent procurement needs where no approved vendor can fulfill the requirement:
1. Department head submits emergency vendor request with written justification
2. Abbreviated due diligence (credit check + basic compliance verification)
3. Temporary approval granted for a single purchase order (max EUR 5,000)
4. Full onboarding must be completed within 30 days of temporary approval

**IMPORTANT:** Purchase orders from unknown vendors should NEVER be auto-approved. They must always be flagged for human review, regardless of order value or other validation results. However, the system should note whether an emergency onboarding request has been submitted when providing context to the reviewer."""),

    ("13. Subsidiary and Parent Company Relationships", """The following vendor relationships should be considered when validating purchase orders:

**Acme Group:**
- Acme Corporation Ltd (VND-002) — Primary entity, registered in UK
- Acme GmbH — German subsidiary, same billing entity as VND-002
- Acme Corp — Common abbreviation, same entity as VND-002
Purchase orders referencing any of these names should be matched to VND-002.

**EuroFasteners Group:**
- EuroFasteners GmbH (VND-006) — Primary entity, registered in Germany
- EuroFasteners Austria GmbH — Austrian subsidiary, separate billing entity (NOT in registry)
Purchase orders from EuroFasteners Austria should be treated as a separate vendor requiring onboarding.

**Important distinction:** Abbreviations and name variations of an approved vendor are acceptable. Orders from a related but separate legal entity (different subsidiary) require that specific entity to be onboarded as a separate vendor."""),
]


# =============================================================================
# DOCUMENT 2: PRODUCT CATALOG
# =============================================================================

CATALOG_SECTIONS = [
    ("1. Overview", """This catalog contains all approved products with their standard pricing, specifications, and procurement guidelines. Catalog prices are updated quarterly and serve as the baseline for price validation on purchase orders.

**Price Validation Rules:**
- Prices within 10% of catalog: Accepted without review
- Prices 10-25% above catalog: Flagged for review (may be valid — check volume discounts, seasonal adjustments, or vendor-specific pricing agreements)
- Prices more than 25% above catalog: Requires written justification from the vendor or requester
- Prices below catalog: Always accepted (indicates negotiated discount)

**IMPORTANT:** Price validation must account for volume discounts, seasonal adjustments, commodity price fluctuations, and vendor-specific framework agreements. A price above catalog is not automatically a violation — context matters."""),

    ("2. Electronics Category", """**SKU-4421 — Industrial Sensor Module**
- Description: 24V DC, IP67 rated, M12 connector
- Standard Unit Price: EUR 12.50 per piece
- Minimum Order Quantity: 10 pieces
- Primary Vendor: TechParts Bulgaria OOD (VND-001)
- Lead Time: 5-10 business days (standard), 3 business days (expedited from TechParts)

Volume Pricing (per framework agreement FA-2024-001 with TechParts):
- 1-99 units: EUR 12.50 (standard catalog price)
- 100-499 units: EUR 11.25 (10% discount)
- 500+ units: EUR 10.00 (20% discount, requires quarterly commitment PO)

Alternative Suppliers: Balkan Electronics EOOD (VND-003) — EUR 13.00 per unit, longer lead time

**SKU-3345 — Programmable Logic Controller**
- Description: 24 digital I/O, Ethernet/IP communication
- Standard Unit Price: EUR 420.00 per piece
- Minimum Order Quantity: 1 piece
- Primary Vendor: TechParts Bulgaria OOD (VND-001)
- Lead Time: 10-15 business days

Note: PLC orders over EUR 5,000 total may qualify for project-based pricing. Contact TechParts account manager for quotation on large PLC deployments.

Product Compatibility Notes:
- Compatible with SKU-4421 sensor modules (same M12 connector standard)
- Requires SKU-9400 DIN Rail Terminal Blocks for installation (minimum 24 per PLC)
- Power supply not included — order separately"""),

    ("3. Mechanical Components Category", """**SKU-7890 — Precision Timing Belt**
- Description: HTD 5M profile, 15mm width, polyurethane construction
- Standard Unit Price: EUR 15.00 per piece
- Minimum Order Quantity: 25 pieces
- Primary Vendor: Acme Corporation Ltd (VND-002)
- Lead Time: 7-14 business days

Volume Pricing (per Acme Corporation contract, effective 2024-07-01):
- 1-49 units: EUR 15.00 (standard catalog price)
- 50-199 units: EUR 13.50 (10% discount)
- 200-499 units: EUR 12.75 (15% discount)
- 500+ units: EUR 12.00 (20% discount)

**IMPORTANT PRICING NOTE:** When validating prices for SKU-7890, the applicable price depends on the order quantity. An order of 100 units at EUR 13.50 per unit is CORRECT (10% volume discount applies). An order at EUR 17.50 for a small quantity may reflect Acme's Q4 seasonal surcharge (5% on mechanical components October-December) plus a small quantity premium. Prices up to EUR 17.25 in Q4 (catalog + 15%) are within normal range and should be reviewed in context, not automatically flagged.

Seasonal Pricing for Mechanical Components from Acme Corporation:
- Standard (Q1-Q3): Catalog price applies
- Q4 (October-December): Up to 5% seasonal surcharge on all mechanical components
- This surcharge is pre-approved under the vendor contract and should not be flagged

**SKU-2250 — Hydraulic Cylinder Seal Kit**
- Description: 50mm bore, NBR (nitrile) material
- Standard Unit Price: EUR 34.00 per kit
- Minimum Order Quantity: 5 kits
- Primary Vendor: Nordic Supply Solutions AB (VND-004)
- Lead Time: 10-15 business days

Storage Note: Seal kits have a shelf life of 24 months. Orders should consider current inventory levels to avoid waste."""),

    ("4. Fasteners Category", """**SKU-1100 — Stainless Steel Hex Bolt**
- Description: M10x40, A2-70 grade stainless steel
- Standard Unit Price: EUR 0.45 per piece
- Minimum Order Quantity: 500 pieces
- Primary Vendor: EuroFasteners GmbH (VND-006)

**SKU-1102 — Stainless Steel Hex Nut**
- Description: M10, A2-70 grade stainless steel
- Standard Unit Price: EUR 0.18 per piece
- Minimum Order Quantity: 500 pieces
- Primary Vendor: EuroFasteners GmbH (VND-006)

**Consignment Stock Note:** Standard fasteners (SKU-1100, SKU-1102) are covered under the consignment stock agreement with EuroFasteners GmbH. Purchase orders for these items may show EUR 0.00 per unit if drawn from consignment stock. This is correct and should NOT be flagged as a pricing anomaly or missing price.

Bulk Pricing for Fasteners (all SKUs from EuroFasteners):
- Orders over 5,000 pieces: 8% discount from catalog
- Orders over 10,000 pieces: 12% discount from catalog
- Consignment replenishment: Invoiced at catalog price minus 5% handling discount"""),

    ("5. Hydraulics Category", """**SKU-2250 — Hydraulic Cylinder Seal Kit**
- See Mechanical Components section for details

**Hydraulic Components General Notes:**
- All hydraulic components must be ordered with material certificates
- Seal materials: NBR for standard applications, FKM (Viton) for high-temperature applications
- FKM seal kits are available as a custom order variant at approximately 2x the NBR price — this premium is expected and should not be flagged as a price mismatch"""),

    ("6. Motors and Drives Category", """**SKU-3010 — 3-Phase AC Motor**
- Description: 2.2kW, 1450 RPM, IE3 efficiency class
- Standard Unit Price: EUR 285.00 per piece
- Minimum Order Quantity: 1 piece
- Primary Vendor: Balkan Electronics EOOD (VND-003)
- Lead Time: 15-20 business days (standard), 5-7 business days (ex-stock if available)

**Capital Equipment Classification:**
Motors above EUR 1,000 total order value are classified as capital equipment and require asset tagging upon receipt. This does not affect the procurement approval process but should be noted in the order.

Motor orders are commonly paired with:
- Variable Frequency Drives (not in standard catalog — request quotation)
- Motor mounting brackets (vendor-specific, order through same vendor)"""),

    ("7. Automation Category", """**SKU-3345 — Programmable Logic Controller**
- See Electronics section for details

**Automation Project Orders:**
Large automation projects (total value over EUR 10,000) may be eligible for project-based pricing from TechParts Bulgaria OOD under framework agreement FA-2024-001. Project pricing typically offers 15-25% discount from catalog but requires a project PO with defined delivery schedule.

Custom Industrial Controllers:
- Custom or non-standard controllers are NOT in the product catalog
- They require vendor quotation and separate approval process
- Typical price range: EUR 800-2,000 per unit depending on specifications
- Lead time: 4-8 weeks for custom configurations
- Common vendors for custom controllers: TechParts Bulgaria OOD (preferred), or new vendor onboarding required"""),

    ("8. Infrastructure Category", """**SKU-5500 — Industrial Cable Tray**
- Description: 300mm wide, galvanized steel, 3m length
- Standard Unit Price: EUR 22.75 per piece
- Minimum Order Quantity: 10 pieces
- Primary Vendor: Plovdiv Industrial Supply AD (VND-005)

**SKU-5520 — Cable Tray Connector Plate**
- Description: 300mm, galvanized steel
- Standard Unit Price: EUR 4.50 per piece
- Minimum Order Quantity: 20 pieces
- Primary Vendor: Plovdiv Industrial Supply AD (VND-005)

**Steel Price Fluctuation Note:**
Infrastructure products made from galvanized steel are subject to commodity price fluctuations. Catalog prices are based on Q1 2025 steel indices. Price deviations of up to 12% from catalog are considered normal for steel products and should be reviewed in context of current market conditions rather than automatically flagged."""),

    ("9. Safety Equipment Category", """**SKU-6010 — Safety Light Curtain**
- Description: Type 4, 600mm protection height, 14mm resolution
- Standard Unit Price: EUR 890.00 per pair
- Minimum Order Quantity: 1 pair
- Primary Vendor: Nordic Supply Solutions AB (VND-004)
- Lead Time: 15-20 business days
- Certification: CE marked, compliant with EN 61496-1

**SKU-6200 — Emergency Stop Push Button**
- Description: 40mm mushroom head, 2NC contacts
- Standard Unit Price: EUR 18.50 per piece
- Minimum Order Quantity: 5 pieces
- Primary Vendor: Nordic Supply Solutions AB (VND-004)

**Safety Equipment Procurement Rules:**
- Safety equipment orders are NEVER subject to automatic approval regardless of value or vendor status
- All safety equipment orders require Engineering sign-off confirming specification compliance
- Exception: Replacement orders for identical equipment (same SKU, same specification) may follow standard approval process if accompanied by a maintenance work order reference"""),

    ("10. Consumables Category", """**SKU-8001 — Thermal Paste**
- Description: 10g tube, 8.5 W/mK thermal conductivity
- Standard Unit Price: EUR 6.80 per tube
- Minimum Order Quantity: 10 tubes
- Primary Vendor: Balkan Electronics EOOD (VND-003)

**SKU-8050 — Industrial Lubricant**
- Description: Synthetic, 5L canister, ISO VG 68
- Standard Unit Price: EUR 42.00 per canister
- Minimum Order Quantity: 2 canisters
- Primary Vendor: Stara Zagora Metals OOD (VND-008)

**Consumables Ordering Guidelines:**
- Consumables under EUR 200 total may be ordered through the simplified procurement process (no PO required, petty cash or corporate card)
- Consumables are not subject to volume discount schedules
- Reorder point system: Warehouse maintains minimum stock levels; reorder POs are automatically generated when stock falls below threshold"""),

    ("11. Electrical Category", """**SKU-9100 — Copper Busbar**
- Description: 30x5mm cross-section, 1m length, electrolytic grade copper
- Standard Unit Price: EUR 28.00 per piece
- Minimum Order Quantity: 5 pieces
- Primary Vendor: Stara Zagora Metals OOD (VND-008)

**Copper Pricing Note:** Copper busbars are subject to London Metal Exchange (LME) price fluctuations. The catalog price of EUR 28.00 is based on Q1 2025 LME copper average. Price deviations of up to 15% from catalog are normal for copper products. The vendor provides LME reference pricing with each quotation.

**SKU-9400 — DIN Rail Terminal Block**
- Description: 2.5mm square, spring clamp, grey
- Standard Unit Price: EUR 1.95 per piece
- Minimum Order Quantity: 50 pieces
- Primary Vendor: Balkan Electronics EOOD (VND-003)

Note: Terminal blocks are a high-volume consumable item. Orders typically range from 100-500 pieces. Bulk orders over 1,000 pieces qualify for a 5% discount."""),

    ("12. Product Substitutions and End-of-Life", """**Currently Active Substitutions:**
- None at this time.

**End-of-Life Notices:**
- No products are currently flagged for end-of-life.

**Substitution Policy:**
When a product reaches end-of-life or becomes unavailable:
1. The vendor must provide at least 90 days notice
2. A substitute product must be identified and validated by Engineering
3. The substitute is added to the catalog with a cross-reference to the original SKU
4. Both SKUs remain valid during the transition period (typically 6 months)
5. Price differences between original and substitute are reviewed by Finance

**Custom and Non-Catalog Items:**
Products not listed in this catalog require:
- A vendor quotation attached to the purchase order
- Department head approval regardless of order value
- If the item exceeds EUR 5,000, Finance review is also required
- Custom items from approved vendors follow standard vendor terms
- Custom items from non-approved vendors require vendor onboarding first"""),
]


# =============================================================================
# DOCUMENT 3: PROCUREMENT POLICIES
# =============================================================================

POLICY_SECTIONS = [
    ("1. Purpose and Scope", """This policy manual establishes comprehensive rules and procedures for all procurement activities within the organization. It applies to all departments and personnel authorized to submit, review, or approve purchase orders.

This document supersedes all previous procurement policy documents. Where this policy conflicts with department-specific procedures, this policy takes precedence unless a formal exception has been granted.

**Policy Document ID:** POL-PROC-2024-01
**Effective Date:** 1 January 2025
**Last Revised:** 15 March 2025
**Next Review:** 1 January 2026"""),

    ("2. Department Spending Limits", """Each department is assigned a maximum per-order spending limit. Any single purchase order exceeding the department limit requires escalation.

**Standard Per-Order Limits:**

Engineering: EUR 5,000.00 per order
Marketing: EUR 5,000.00 per order
Operations: EUR 10,000.00 per order
Finance: EUR 15,000.00 per order
HR: EUR 3,000.00 per order

**Limit Escalation Process:**
When a purchase order exceeds the department limit:
1. The order is flagged for review (not automatically rejected)
2. The department head must provide written justification
3. Finance department reviews and approves or denies the exception
4. For orders exceeding 2x the department limit, CFO approval is required

**Quarterly Budget Exceptions:**
Each department may request a quarterly budget exception for planned capital expenditures that exceed the per-order limit. The process is:
1. Submit a Capital Expenditure Request (CAPEX) form to Finance by the 15th of the month before the quarter begins
2. Finance reviews and approves a temporary increased limit for the specific quarter
3. Approved CAPEX exceptions are documented and communicated to the procurement team
4. Purchase orders under an approved CAPEX exception should reference the CAPEX approval number

**Cross-Department Orders:**
When a purchase order serves multiple departments, the spending limit of the primary (requesting) department applies. However, the total cost may be split across department budgets with appropriate cost center codes.

**End-of-Year Budget Considerations:**
- Q4 purchase orders (October-December) are subject to remaining annual budget availability
- Departments may not exceed their annual budget allocation through accumulated purchase orders
- Carry-over of unused budget to the following year is not permitted"""),

    ("3. Payment Terms Policy", """**Maximum Allowed Payment Terms: Net 30**

Acceptable payment terms for standard purchase orders:
- Net 15 — Payment due within 15 calendar days of invoice date
- Net 30 — Payment due within 30 calendar days of invoice date (maximum standard)
- Due on Receipt — Payment due immediately upon receipt of invoice

**Extended Payment Terms (Net 45, Net 60, Net 90):**
Extended payment terms beyond Net 30 are not permitted under standard policy. However, exceptions may be granted in the following circumstances:

1. **Framework Agreement Exception:** If a vendor's framework agreement explicitly includes extended payment terms (e.g., Net 45 for large project orders), these terms are acceptable when the PO references the framework agreement number. Currently, no active framework agreements include terms beyond Net 30.

2. **Capital Equipment Exception:** For capital equipment purchases exceeding EUR 10,000, Net 45 terms may be approved by Finance on a case-by-case basis. This requires:
   - Written request from the department head
   - Finance department approval
   - Documented justification (e.g., equipment delivery and commissioning timeline)

3. **International Vendor Exception:** For vendors outside the EU, Net 45 may be approved to accommodate longer shipping and customs processing times. This requires Finance pre-approval.

**Early Payment Discounts:**
When vendors offer early payment discounts (e.g., 2/10 Net 30 — 2% discount if paid within 10 days), Finance should be notified to take advantage of the discount. Early payment discounts are always encouraged.

**IMPORTANT:** A purchase order listing Net 60 payment terms from a domestic EU vendor without a framework agreement or capital equipment justification is a hard violation and should not be approved without Finance exception approval."""),

    ("4. Approval Thresholds and Workflow", """Purchase orders are subject to approval requirements based on total order value, independent of department spending limits.

**Approval Matrix:**

Up to EUR 500.00: Automatic approval (no human review required), provided all other validation checks pass (vendor approved, pricing within tolerance, all required fields present).

EUR 500.01 to EUR 2,500.00: Department manager approval required. The department manager is the requester's direct supervisor.

EUR 2,500.01 to EUR 10,000.00: Department head approval plus Finance review. Both approvals must be obtained before the order is placed.

Over EUR 10,000.00: Executive approval required. The CFO or an authorized delegate must approve the order. For orders over EUR 25,000.00, Board notification is required (approval is at CFO discretion).

**Approval Delegation:**
- Department managers may delegate approval authority to a designated deputy for orders up to EUR 2,500 during planned absences
- Department heads may delegate to managers for orders up to EUR 5,000 during planned absences
- CFO delegation is limited to the Deputy CFO or Finance Director
- All delegations must be documented in writing and filed with the Procurement department

**Emergency Approval Process:**
For urgent orders where the normal approver is unavailable:
1. Orders up to EUR 5,000: Any department head may approve with written justification
2. Orders up to EUR 10,000: CFO or Deputy CFO must be reached (24-hour response SLA)
3. Orders over EUR 10,000: Cannot be approved through emergency process — must wait for proper authorization

**IMPORTANT for Automated Processing:**
The automated system handles Tier 1 (up to EUR 500) approval automatically. Orders in higher tiers are flagged for the appropriate level of human review. The system should clearly indicate which approval tier applies when flagging an order."""),

    ("5. Required Fields for Purchase Orders", """Every purchase order must include specific fields for processing. Missing fields trigger validation flags of varying severity.

**Mandatory Fields (Hard Rejection if Missing):**
- PO Number — Unique identifier for the purchase order
- Vendor Name — Must match an approved vendor in the registry
- Line Items — At least one item with description and quantity
- Total Amount — Sum of all line items
- Currency — Must be an approved currency (EUR, BGN, USD)
- Delivery Date — Expected delivery date

**Strongly Recommended Fields (Soft Flag if Missing):**
- Vendor Contact Email — Used for order confirmation and communication
- SKU/Part Number — Required for catalog price validation
- Unit Price — Required for pricing compliance validation
- Requester Name — Identifies the person requesting the purchase
- Requester Department — Required for spending limit validation
- Payment Terms — Required for payment terms compliance

**Conditional Requirements:**
- If the order total exceeds EUR 2,500: Requester department becomes mandatory (hard requirement) for spending limit validation
- If any line item references a safety equipment SKU (SKU-6010, SKU-6200): Engineering sign-off field is mandatory
- If payment terms are Net 45 or longer: Finance pre-approval reference number is mandatory

**Missing PO Number:**
Purchase orders without a PO number cannot be processed in the standard workflow. However, some vendors generate their own PO numbers upon order confirmation. In such cases, the system should flag the missing PO number as a soft issue (not hard rejection) and note that the vendor will provide a PO number upon confirmation."""),

    ("6. Currency Policy", """**Approved Currencies:**
- EUR (Euro) — Preferred currency for all transactions
- BGN (Bulgarian Lev) — Accepted for domestic Bulgarian vendors
- USD (United States Dollar) — Accepted for international vendors outside Europe

**Currency Conversion:**
- BGN to EUR conversion uses the fixed rate of 1.9558 BGN = 1 EUR (official fixed rate)
- USD to EUR conversion uses the ECB reference rate at the time of order placement
- All spending limits and approval thresholds are denominated in EUR
- For orders in BGN or USD, the EUR equivalent is used for limit and threshold checks

**Non-Standard Currencies:**
Orders in currencies other than EUR, BGN, or USD require Finance pre-approval. Common cases include:
- GBP for UK vendors (e.g., Acme Corporation Ltd may invoice in GBP)
- SEK for Swedish vendors (e.g., Nordic Supply Solutions AB)
- In practice, both Acme Corporation Ltd and Nordic Supply Solutions AB invoice in EUR per their contract terms"""),

    ("7. Minimum and Maximum Order Values", """**Minimum Order Value: EUR 50.00**
Orders below EUR 50.00 should be consolidated with other procurement needs or handled through the petty cash process. The automated system will flag orders below this threshold.

**Exception:** Consumable reorder POs generated automatically by the warehouse management system may be below EUR 50.00. These are pre-approved and should not be flagged.

**Maximum Single Order Value:**
There is no explicit maximum order value, but orders above certain thresholds trigger additional approval requirements:
- Over EUR 10,000: Executive approval required
- Over EUR 25,000: Board notification required
- Over EUR 50,000: Board approval required
- Over EUR 100,000: Competitive bidding process required (minimum 3 vendor quotations)

**Order Splitting Prohibition:**
Deliberately splitting a single procurement need into multiple smaller orders to avoid approval thresholds is a policy violation. The system monitors for patterns of closely-timed orders from the same vendor/department."""),

    ("8. Vendor Compliance Requirements", """All vendors referenced in purchase orders must meet the following criteria:

**Active Registration:**
- The vendor must be listed in the Approved Vendor Registry
- The vendor's contract status must be "active"
- Vendor names on purchase orders must match the registered name or a recognized abbreviation

**Name Matching Rules:**
- Exact matches are always accepted
- Common abbreviations documented in the vendor profile are accepted (e.g., "Acme Corp" for "Acme Corporation Ltd")
- Minor variations such as missing legal suffixes (OOD, GmbH, Ltd, BV, AB, AD, SRL) are flagged as soft issues for verification but generally accepted
- Completely different names are flagged as unknown vendors (hard flag)

**Expired Contract Handling:**
- Vendors with expired contracts are not eligible for automatic approval
- If a contract renewal is in progress (documented in vendor profile), a 90-day grace period applies
- During the grace period, orders are flagged with a soft issue (not hard rejection)
- After the grace period, orders are treated as unknown vendor orders (hard flag)

**Vendor Blacklist:**
The organization does not currently maintain a vendor blacklist. All unknown vendors are treated the same way: flagged for review and manual vendor onboarding.

**New Vendor Assessment:**
New vendor orders require:
- Standard process: 10 business days for due diligence and onboarding
- Emergency process: 3-5 business days with abbreviated checks (single PO up to EUR 5,000)"""),

    ("9. Pricing Compliance and Validation", """**Standard Price Validation:**
Unit prices are compared against the current product catalog. Deviations are assessed relative to the catalog price.

**Deviation Thresholds:**
- Within 10% of catalog price: Accepted without flag
- 10-25% above catalog price: Soft flag for review
- More than 25% above catalog price: Hard flag requiring justification
- Below catalog price: Always accepted (negotiated discount)

**IMPORTANT — Context-Dependent Pricing:**
The following situations may cause legitimate price deviations that should NOT be treated as violations:

1. **Volume Discounts:** Many vendors offer tiered pricing based on order quantity. A price below catalog for a large order is expected. Refer to the vendor profile for specific discount schedules.

2. **Volume Premiums:** Small quantity orders (below standard MOQ) may carry a premium. A price 10-15% above catalog for a very small order may be legitimate.

3. **Seasonal Adjustments:** Some vendors apply seasonal surcharges (e.g., Acme Corporation Q4 surcharge of 5% on mechanical components). These are pre-approved under the vendor contract.

4. **Commodity Price Fluctuations:** Products linked to commodity prices (copper, steel, aluminum) may deviate from catalog based on current market conditions. The vendor should provide market reference with the quotation.

5. **Consignment Stock Pricing:** Items drawn from consignment stock may show EUR 0.00 per unit (invoiced separately). This is correct under consignment agreements.

6. **Custom or Non-Catalog Items:** Items not in the standard catalog have no reference price. The system should note the absence of a catalog reference rather than flagging a price mismatch.

7. **Framework Agreement Pricing:** Vendors with framework agreements may have pricing that differs from the general catalog. Framework pricing supersedes catalog pricing.

**Price Validation Priority:**
1. Check framework agreement pricing first (if applicable)
2. Then check volume discount tiers (if applicable)
3. Then compare against standard catalog price
4. Apply seasonal adjustment consideration (if applicable)
5. Consider commodity price fluctuation allowance (if applicable)"""),

    ("10. Duplicate Order Prevention", """The system checks for potential duplicate orders using the following criteria:

**Duplicate Detection Rules:**
- Same vendor name AND same total amount within a 7-day window: Flagged as potential duplicate
- Same vendor name AND same line items (by SKU) within a 14-day window: Flagged as potential duplicate

**Known Non-Duplicate Patterns:**
- Monthly recurring orders for consumables (same vendor, similar amounts) are NOT duplicates
- Multiple orders from the same vendor for different departments are NOT duplicates
- Orders with different delivery dates more than 30 days apart are NOT duplicates
- Consignment replenishment orders are NOT duplicates even if amounts are similar"""),

    ("11. Emergency and Urgent Procurement", """**Emergency Procurement Procedure:**
For situations where immediate procurement is required and standard approval timelines cannot be met:

**Definition of Emergency:**
- Production line stoppage due to equipment failure
- Safety-critical component replacement
- Regulatory compliance deadline
- Customer delivery commitment at risk

**Emergency PO Processing Rules:**
1. Emergency purchase orders must include "URGENT" or "EMERGENCY" in the subject or notes
2. Emergency orders from approved vendors up to EUR 5,000 may be processed with department head verbal approval (documented within 24 hours)
3. Emergency orders from approved vendors EUR 5,000-10,000 require Finance verbal approval (documented within 24 hours)
4. Emergency orders from unapproved vendors: maximum EUR 5,000, requires both department head and Finance verbal approval
5. Emergency orders exceeding EUR 10,000 from any vendor cannot bypass the standard approval process

**Post-Emergency Documentation:**
All emergency orders must be documented with:
- Written justification filed within 48 hours
- Impact assessment (cost of delay vs. cost of emergency procurement)
- Root cause analysis (why was the need not anticipated?)
- Preventive measures to avoid future emergencies

**IMPORTANT for Automated Processing:**
When a purchase order contains "urgent" or "emergency" language, the system should:
- Note the urgency in the processing metadata
- Still apply all validation checks
- Flag the urgency to the reviewer for expedited review
- Do NOT auto-approve emergency orders even if they would otherwise qualify"""),

    ("12. Policy Exceptions and Override Process", """**Standard Exception Process:**
Any exception to this procurement policy requires:
1. Written request from the department head
2. Finance department review and approval
3. Documentation of the exception rationale
4. Tracking in the exception log for quarterly audit

**Pre-Approved Exceptions:**
The following situations are pre-approved exceptions and do not require the standard exception process:
- Consignment stock drawdowns at EUR 0.00 per unit (covered under consignment agreements)
- Q4 seasonal surcharges from Acme Corporation Ltd (up to 5% on mechanical components)
- Commodity price fluctuations up to 15% for copper and steel products
- Volume discount pricing that differs from standard catalog
- Vendor contract renewal grace period orders (90-day window)

**Exception Tracking:**
All exceptions (standard and pre-approved) are logged and reviewed quarterly by the Finance department. Patterns of frequent exceptions may trigger policy revision.

**Audit Requirements:**
- All policy exceptions are subject to internal audit
- Exception documentation must be retained for 7 years
- Quarterly exception reports are submitted to the CFO"""),

    ("13. Cross-Department Procurement", """**Shared Resource Procurement:**
When procurement serves multiple departments:
- The requesting department bears the primary approval responsibility
- Cost may be split across departments using cost center codes
- The spending limit of the primary department applies to the full order value
- Split orders to circumvent spending limits are prohibited

**Centralized Procurement Items:**
The following items are procured centrally by the Operations department regardless of which department needs them:
- IT equipment and software (through IT procurement process)
- Office supplies (through facilities management)
- Safety equipment (through Health & Safety)
- Vehicle fleet and transportation (through Fleet Management)

Individual departments should not submit POs for centralized items — these will be flagged and redirected."""),

    ("14. Vendor Payment and Invoice Processing", """**Invoice Matching:**
All invoices are matched against the corresponding purchase order:
- Three-way match: PO, goods receipt, and invoice must align
- Tolerance: Invoice amount within 2% of PO amount is automatically accepted
- Invoices exceeding PO amount by more than 2% require buyer approval

**Payment Processing:**
- Payments are processed weekly on Fridays
- Emergency payments may be processed on any business day with Finance approval
- International wire transfers require 3 business days processing time

**Vendor Credit Terms:**
- Vendors with good payment history (>12 months, no disputes) may be eligible for extended terms upon request
- New vendors start with Due on Receipt for the first 3 orders, then transition to their contracted terms"""),

    ("15. Contact Information and Support", """**Procurement Department:**
- Email: procurement@company.bg
- Phone: +359 2 123 4567
- Hours: Monday-Friday, 08:30-17:30 EET
- Emergency (outside hours): +359 888 123 456

**Finance Department:**
- Email: finance@company.bg
- Accounts Payable: ap@company.bg
- Phone: +359 2 123 4568

**System Support:**
- Email: it-support@company.bg
- PO Processing System Issues: po-support@company.bg

**Escalation Path:**
1. First contact: Procurement department
2. If unresolved: Finance department
3. If unresolved: CFO office
4. Policy interpretation disputes: Legal department"""),
]


def _generate_pdf(filename: str, title: str, subtitle: str, doc_id: str, effective_date: str, sections: list[tuple[str, str]]) -> None:
    """Generate a PDF from sections."""
    doc = pymupdf.Document()

    # Title page
    _write_title_page(doc, title, subtitle, doc_id, effective_date)

    # Content pages
    page = _add_page(doc)
    y = MARGIN_TOP

    for section_title, section_body in sections:
        page, y = _write_section(doc, page, y, section_title, section_body)
        y += 10  # Extra spacing between sections

    page_count = doc.page_count
    doc.save(filename)
    doc.close()
    print(f"Generated: {filename} ({page_count} pages)")


def main():
    _generate_pdf(
        filename="pdfs/approved_vendor_registry.pdf",
        title="Approved Vendor Registry",
        subtitle="Vendor Profiles, Contracts, and Relationship Guide",
        doc_id="REG-VEND-2025-01",
        effective_date="1 January 2025",
        sections=VENDOR_SECTIONS,
    )

    _generate_pdf(
        filename="pdfs/product_catalog.pdf",
        title="Product Catalog",
        subtitle="Approved Products, Pricing, and Procurement Guidelines",
        doc_id="CAT-PROD-2025-01",
        effective_date="1 January 2025",
        sections=CATALOG_SECTIONS,
    )

    _generate_pdf(
        filename="pdfs/procurement_policies.pdf",
        title="Corporate Procurement Policy Manual",
        subtitle="Rules, Procedures, and Exception Handling",
        doc_id="POL-PROC-2024-01",
        effective_date="1 January 2025",
        sections=POLICY_SECTIONS,
    )

    print("\nAll knowledge base PDFs generated in pdfs/ directory.")


if __name__ == "__main__":
    main()
