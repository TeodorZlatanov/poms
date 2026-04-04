import type {
  PurchaseOrder,
  OrderDetail,
  AnalyticsData,
  OrderListResponse,
} from "@/types";

// ── Three sample orders matching the demo PO files ──

const ORDER_CLEAN_ID = "a1b2c3d4-0001-4000-8000-000000000001";
const ORDER_FUZZY_ID = "a1b2c3d4-0002-4000-8000-000000000002";
const ORDER_BAD_ID = "a1b2c3d4-0003-4000-8000-000000000003";

// ── List view (OrderSummary) ──

export const mockOrders: PurchaseOrder[] = [
  {
    id: ORDER_BAD_ID,
    po_number: "PO-2024-0049",
    vendor_name: "Zylux Dynamics",
    total_amount: 24750.0,
    currency: "EUR",
    status: "REJECTED",
    issue_tags: ["UNKNOWN_VENDOR", "MISSING_FIELD", "OVER_LIMIT"],
    created_at: "2026-04-04T09:15:00Z",
  },
  {
    id: ORDER_FUZZY_ID,
    po_number: "PO-2024-0048",
    vendor_name: "Acme Industreis",
    total_amount: 3625.0,
    currency: "EUR",
    status: "PENDING_REVIEW",
    issue_tags: ["VENDOR_FUZZY_MATCH", "PRICE_MISMATCH"],
    created_at: "2026-04-04T08:45:00Z",
  },
  {
    id: ORDER_CLEAN_ID,
    po_number: "PO-2024-0047",
    vendor_name: "Acme Industries",
    total_amount: 1250.0,
    currency: "EUR",
    status: "APPROVED",
    issue_tags: [],
    created_at: "2026-04-04T08:30:00Z",
  },
];

// ── Detail views ──

export const mockOrderDetails: Record<string, OrderDetail> = {
  [ORDER_CLEAN_ID]: {
    id: ORDER_CLEAN_ID,
    po_number: "PO-2024-0047",
    po_date: "2026-04-03",
    vendor_name: "Acme Industries",
    vendor_contact: "sales@acme-industries.com",
    requester_name: "Sarah Chen",
    requester_department: "Engineering",
    line_items: {
      items: [
        {
          description: "Wireless Keyboard K380",
          sku: "KB-380-BLK",
          quantity: 10,
          unit_price: 49.99,
        },
        {
          description: 'LED Monitor 27"',
          sku: "MON-27-4K",
          quantity: 5,
          unit_price: 149.99,
        },
      ],
    },
    total_amount: 1250.0,
    currency: "EUR",
    delivery_date: "2026-04-18",
    payment_terms: "Net 30",
    status: "APPROVED",
    confidence_score: 0.97,
    original_filename: "po_clean.pdf",
    sender_email: "purchasing@acme-industries.com",
    created_at: "2026-04-04T08:30:00Z",
    updated_at: "2026-04-04T08:30:12Z",
    validation_results: [
      { check_type: "vendor_check", result: "PASS", details: { vendor_id: "V-1001", match: "exact" } },
      { check_type: "price_check", result: "PASS", details: { max_deviation: "2.1%", threshold: "10%" } },
      { check_type: "policy_check", result: "PASS", details: { payment_terms: "within policy", spending_limit: "under limit" } },
      { check_type: "completeness_check", result: "PASS", details: { missing_fields: "none" } },
    ],
    issue_tags: [],
    emails: [
      {
        direction: "INBOUND",
        email_type: "PO_SUBMISSION",
        sender: "purchasing@acme-industries.com",
        recipient: "po-intake@company.com",
        subject: "PO-2024-0047 — Office Equipment",
        sent_at: "2026-04-04T08:29:45Z",
      },
      {
        direction: "OUTBOUND",
        email_type: "CONFIRMATION",
        sender: "po-intake@company.com",
        recipient: "purchasing@acme-industries.com",
        subject: "PO-2024-0047 Approved — Order Confirmed",
        sent_at: "2026-04-04T08:30:12Z",
      },
    ],
    processing_logs: [
      { step: "file_processing", status: "COMPLETED", duration_ms: 320 },
      { step: "classification", status: "COMPLETED", duration_ms: 1150 },
      { step: "extraction", status: "COMPLETED", duration_ms: 2840 },
      { step: "validation", status: "COMPLETED", duration_ms: 680 },
      { step: "routing", status: "COMPLETED", duration_ms: 45 },
      { step: "persist", status: "COMPLETED", duration_ms: 120 },
    ],
    review: null,
  },

  [ORDER_FUZZY_ID]: {
    id: ORDER_FUZZY_ID,
    po_number: "PO-2024-0048",
    po_date: "2026-04-03",
    vendor_name: "Acme Industreis",
    vendor_contact: "orders@acmeindustreis.com",
    requester_name: "Marcus Rivera",
    requester_department: "Marketing",
    line_items: {
      items: [
        {
          description: "Ergonomic Office Chair",
          sku: "CHR-ERG-PRO",
          quantity: 5,
          unit_price: 425.0,
        },
        {
          description: "Standing Desk Converter",
          sku: "DSK-STD-36",
          quantity: 5,
          unit_price: 299.99,
        },
      ],
    },
    total_amount: 3625.0,
    currency: "EUR",
    delivery_date: "2026-04-25",
    payment_terms: "Net 30",
    status: "PENDING_REVIEW",
    confidence_score: 0.62,
    original_filename: "po_fuzzy.pdf",
    sender_email: "marcus.r@company.com",
    created_at: "2026-04-04T08:45:00Z",
    updated_at: "2026-04-04T08:45:18Z",
    validation_results: [
      {
        check_type: "vendor_check",
        result: "WARNING",
        details: { query: "Acme Industreis", best_match: "Acme Industries", similarity: "0.91" },
      },
      {
        check_type: "price_check",
        result: "WARNING",
        details: { item: "Ergonomic Office Chair", catalog_price: "€389.00", po_price: "€425.00", deviation: "9.3%" },
      },
      { check_type: "policy_check", result: "PASS", details: { payment_terms: "within policy" } },
      { check_type: "completeness_check", result: "PASS", details: { missing_fields: "none" } },
    ],
    issue_tags: [
      { tag: "VENDOR_FUZZY_MATCH", severity: "SOFT", description: "Vendor name 'Acme Industreis' is similar to 'Acme Industries' (91% match)" },
      { tag: "PRICE_MISMATCH", severity: "SOFT", description: "Ergonomic Office Chair priced at €425.00 vs catalog €389.00 (9.3% over)" },
    ],
    emails: [
      {
        direction: "INBOUND",
        email_type: "PO_SUBMISSION",
        sender: "marcus.r@company.com",
        recipient: "po-intake@company.com",
        subject: "PO-2024-0048 — Office Furniture",
        sent_at: "2026-04-04T08:44:30Z",
      },
      {
        direction: "OUTBOUND",
        email_type: "ACKNOWLEDGMENT",
        sender: "po-intake@company.com",
        recipient: "marcus.r@company.com",
        subject: "PO-2024-0048 — Under Review",
        sent_at: "2026-04-04T08:45:18Z",
      },
    ],
    processing_logs: [
      { step: "file_processing", status: "COMPLETED", duration_ms: 290 },
      { step: "classification", status: "COMPLETED", duration_ms: 980 },
      { step: "extraction", status: "COMPLETED", duration_ms: 3120 },
      { step: "validation", status: "COMPLETED", duration_ms: 1450 },
      { step: "routing", status: "COMPLETED", duration_ms: 38 },
      { step: "persist", status: "COMPLETED", duration_ms: 95 },
    ],
    review: null,
  },

  [ORDER_BAD_ID]: {
    id: ORDER_BAD_ID,
    po_number: "PO-2024-0049",
    po_date: "2026-04-04",
    vendor_name: "Zylux Dynamics",
    vendor_contact: null,
    requester_name: "Jordan Blake",
    requester_department: "Operations",
    line_items: {
      items: [
        {
          description: "Industrial Sensor Array",
          sku: null,
          quantity: 50,
          unit_price: 345.0,
        },
        {
          description: "Control Module v4",
          sku: null,
          quantity: 10,
          unit_price: 750.0,
        },
      ],
    },
    total_amount: 24750.0,
    currency: "EUR",
    delivery_date: null,
    payment_terms: "Net 60",
    status: "REJECTED",
    confidence_score: 0.31,
    original_filename: "po_bad.pdf",
    sender_email: "jblake@zyluxdyn.com",
    created_at: "2026-04-04T09:15:00Z",
    updated_at: "2026-04-04T09:15:22Z",
    validation_results: [
      {
        check_type: "vendor_check",
        result: "FAIL",
        details: { query: "Zylux Dynamics", best_match: "none", note: "Not in vendor registry" },
      },
      {
        check_type: "price_check",
        result: "FAIL",
        details: { note: "Cannot verify — products not in catalog" },
      },
      {
        check_type: "policy_check",
        result: "FAIL",
        details: { payment_terms: "Net 60 exceeds max Net 45", spending: "€24,750 exceeds Operations limit of €15,000" },
      },
      {
        check_type: "completeness_check",
        result: "WARNING",
        details: { missing_fields: "vendor_contact, delivery_date, SKUs" },
      },
    ],
    issue_tags: [
      { tag: "UNKNOWN_VENDOR", severity: "HARD", description: "Vendor 'Zylux Dynamics' not found in vendor registry" },
      { tag: "UNKNOWN_PRODUCT", severity: "SOFT", description: "SKUs not found in product catalog" },
      { tag: "OVER_LIMIT", severity: "HARD", description: "Order total €24,750 exceeds Operations department limit of €15,000" },
      { tag: "TERMS_VIOLATION", severity: "HARD", description: "Net 60 payment terms exceed maximum allowed Net 45" },
      { tag: "MISSING_FIELD", severity: "SOFT", description: "Missing vendor contact, delivery date, and product SKUs" },
    ],
    emails: [
      {
        direction: "INBOUND",
        email_type: "PO_SUBMISSION",
        sender: "jblake@zyluxdyn.com",
        recipient: "po-intake@company.com",
        subject: "PO-2024-0049 — Sensor Equipment",
        sent_at: "2026-04-04T09:14:30Z",
      },
      {
        direction: "OUTBOUND",
        email_type: "ACKNOWLEDGMENT",
        sender: "po-intake@company.com",
        recipient: "jblake@zyluxdyn.com",
        subject: "PO-2024-0049 — Requires Review (Issues Found)",
        sent_at: "2026-04-04T09:15:22Z",
      },
    ],
    processing_logs: [
      { step: "file_processing", status: "COMPLETED", duration_ms: 310 },
      { step: "classification", status: "COMPLETED", duration_ms: 1080 },
      { step: "extraction", status: "COMPLETED", duration_ms: 2960 },
      { step: "validation", status: "COMPLETED", duration_ms: 1820 },
      { step: "routing", status: "COMPLETED", duration_ms: 42 },
      { step: "persist", status: "COMPLETED", duration_ms: 110 },
    ],
    review: null,
  },
};

// ── Analytics ──

export const mockAnalytics: AnalyticsData = {
  total_processed: 3,
  by_status: {
    APPROVED: 1,
    PENDING_REVIEW: 1,
    REJECTED: 1,
  },
  approval_rate: 0.333,
  common_tags: [
    { tag: "UNKNOWN_VENDOR", count: 1 },
    { tag: "OVER_LIMIT", count: 1 },
    { tag: "TERMS_VIOLATION", count: 1 },
    { tag: "VENDOR_FUZZY_MATCH", count: 1 },
    { tag: "PRICE_MISMATCH", count: 1 },
    { tag: "MISSING_FIELD", count: 1 },
    { tag: "UNKNOWN_PRODUCT", count: 1 },
  ],
  avg_processing_time_ms: 4483,
  volume_by_day: [
    { date: "2026-03-29", count: 0 },
    { date: "2026-03-30", count: 0 },
    { date: "2026-03-31", count: 2 },
    { date: "2026-04-01", count: 5 },
    { date: "2026-04-02", count: 3 },
    { date: "2026-04-03", count: 8 },
    { date: "2026-04-04", count: 3 },
  ],
};

// ── Helpers for API mock layer ──

export function getMockOrderList(
  filters: { status?: string; vendor?: string; page?: number; page_size?: number } = {},
): OrderListResponse {
  let items = [...mockOrders];

  if (filters.status) {
    items = items.filter((o) => o.status === filters.status);
  }
  if (filters.vendor) {
    const q = filters.vendor.toLowerCase();
    items = items.filter((o) =>
      o.vendor_name?.toLowerCase().includes(q),
    );
  }

  const page = filters.page ?? 1;
  const pageSize = filters.page_size ?? 20;
  const start = (page - 1) * pageSize;

  return {
    items: items.slice(start, start + pageSize),
    total: items.length,
    page,
    page_size: pageSize,
  };
}
