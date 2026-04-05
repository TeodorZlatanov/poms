import {
  CheckCircle,
  XCircle,
  Warning,
  Question,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { ValidationCheck } from "@/types";
import { cn } from "@/utils/cn";

const resultStyles: Record<
  string,
  { icon: Icon; className: string; borderClassName: string; label: string }
> = {
  PASS: {
    icon: CheckCircle,
    className: "text-green-600 dark:text-green-400",
    borderClassName: "border-green-200 dark:border-green-800",
    label: "Passed",
  },
  FAIL: {
    icon: XCircle,
    className: "text-red-600 dark:text-red-400",
    borderClassName: "border-red-200 dark:border-red-800",
    label: "Failed",
  },
  WARNING: {
    icon: Warning,
    className: "text-amber-600 dark:text-amber-400",
    borderClassName: "border-amber-200 dark:border-amber-800",
    label: "Warning",
  },
};

const checkLabels: Record<string, { title: string; description: string }> = {
  VENDOR: {
    title: "Vendor Check",
    description: "Verified against approved vendor registry",
  },
  PRICE: {
    title: "Price Check",
    description: "Compared prices against product catalog",
  },
  POLICY: {
    title: "Policy Check",
    description: "Validated spending limits and payment terms",
  },
  COMPLETENESS: {
    title: "Completeness",
    description: "Verified all required fields are present",
  },
  RAG: {
    title: "AI Review",
    description: "Knowledge base review of validation results",
  },
};

// --- Human-readable field names ---

const FIELD_LABELS: Record<string, string> = {
  po_number: "PO number",
  vendor_name: "vendor name",
  "vendor.name": "vendor name",
  "vendor.contact": "vendor contact email",
  vendor_contact: "vendor contact email",
  total_amount: "total amount",
  currency: "currency",
  delivery_date: "delivery date",
  payment_terms: "payment terms",
  requester_name: "requester name",
  "requester.name": "requester name",
  "requester.department": "requester department",
};

function humanizeFieldMessage(msg: string): string {
  // "Required field 'po_number' is missing" → "PO number is missing (required)"
  const reqMatch = msg.match(/Required field '([^']+)' is missing/);
  if (reqMatch) {
    const label = FIELD_LABELS[reqMatch[1]] ?? reqMatch[1];
    return `${label.charAt(0).toUpperCase() + label.slice(1)} is missing (required)`;
  }
  // "Recommended field 'line_items[0].sku' is missing" → "Item SKU is missing"
  const recMatch = msg.match(/Recommended field '([^']+)' is missing/);
  if (recMatch) {
    const raw = recMatch[1];
    if (raw.includes("sku")) return "Item SKU/part number is missing";
    const label = FIELD_LABELS[raw] ?? raw;
    return `${label.charAt(0).toUpperCase() + label.slice(1)} is missing`;
  }
  return msg;
}

// --- Detail formatters ---

function formatVendorDetails(details: Record<string, unknown>): string[] {
  const name = details.vendor_name;
  const match = details.match_type;
  if (name && match === "PASS") return [`${name} is an approved vendor`];
  if (name && match === "WARNING")
    return [`"${name}" is a close match to an approved vendor`];
  if (name && match === "FAIL")
    return [`"${name}" is not in the approved vendor registry`];
  return [];
}

function formatPriceDetails(details: Record<string, unknown>): string[] {
  const lines: string[] = [];
  const checked = details.items_checked;
  if (typeof checked === "number") {
    lines.push(
      `${checked} item${checked !== 1 ? "s" : ""} checked against catalog`,
    );
  }
  const mismatches = details.mismatches;
  if (Array.isArray(mismatches) && mismatches.length > 0) {
    for (const m of mismatches) {
      const obj = m as Record<string, unknown>;
      const pct = Number(obj.deviation_pct ?? 0);
      lines.push(
        `${obj.sku ?? "Item"}: priced at ${obj.po_price} but catalog lists ${obj.catalog_price} (${pct.toFixed(1)}% higher)`,
      );
    }
  } else if (typeof checked === "number" && checked > 0) {
    lines.push("All prices within acceptable range");
  }
  return lines;
}

function formatPolicyDetails(details: Record<string, unknown>): string[] {
  const lines: string[] = [];
  const dept = details.department;
  const limit = details.limit;
  const total = details.total_amount;
  if (dept && limit != null && total != null) {
    const totalNum = Number(total);
    const limitNum = Number(limit);
    if (totalNum <= limitNum) {
      lines.push(
        `${dept} department: ${totalNum.toLocaleString()} within ${limitNum.toLocaleString()} limit`,
      );
    } else {
      lines.push(
        `${dept} department: ${totalNum.toLocaleString()} exceeds ${limitNum.toLocaleString()} limit`,
      );
    }
  }
  const terms = details.payment_terms;
  if (terms) lines.push(`Payment terms: ${terms}`);
  return lines;
}

function formatCompletenessDetails(
  details: Record<string, unknown>,
): string[] {
  const lines: string[] = [];
  const hard = details.hard_missing;
  const soft = details.soft_missing;
  if (Array.isArray(hard) && hard.length > 0) {
    for (const msg of hard) lines.push(humanizeFieldMessage(String(msg)));
  }
  if (Array.isArray(soft) && soft.length > 0) {
    for (const msg of soft) lines.push(humanizeFieldMessage(String(msg)));
  }
  if (lines.length === 0) lines.push("All required fields present");
  return lines;
}

function formatRagDetails(details: Record<string, unknown>): string[] {
  const lines: string[] = [];
  const summary = details.summary;
  if (typeof summary === "string") lines.push(summary);

  const adjustments = details.adjustments;
  if (Array.isArray(adjustments)) {
    for (const adj of adjustments) {
      const a = adj as Record<string, unknown>;
      const action = String(a.action ?? "").toLowerCase();
      if (action === "keep") continue;
      const reason = a.reasoning;
      if (reason) {
        const verb =
          action === "remove"
            ? "Cleared"
            : action === "upgrade"
              ? "Escalated"
              : action === "downgrade"
                ? "Reduced"
                : action;
        lines.push(`${verb}: ${reason}`);
      }
    }
  }
  return lines;
}

function getDetailLines(
  checkType: string,
  details: Record<string, unknown> | null,
): string[] {
  if (!details || Object.keys(details).length === 0) return [];
  switch (checkType) {
    case "VENDOR":
      return formatVendorDetails(details);
    case "PRICE":
      return formatPriceDetails(details);
    case "POLICY":
      return formatPolicyDetails(details);
    case "COMPLETENESS":
      return formatCompletenessDetails(details);
    case "RAG":
      return formatRagDetails(details);
    default:
      return [];
  }
}

export function ValidationResults({
  checks,
}: {
  checks: ValidationCheck[];
}) {
  if (checks.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-muted">
        <Question size={28} weight="duotone" className="opacity-50" />
        <p className="text-sm">No validation results.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {checks.map((check, i) => {
        const style = resultStyles[check.result] ?? {
          icon: Question,
          className: "text-muted",
          borderClassName: "border-border",
          label: check.result,
        };
        const ResultIcon = style.icon;
        const meta = checkLabels[check.check_type];
        const title = meta?.title ?? check.check_type;
        const subtitle = meta?.description ?? "";
        const lines = getDetailLines(check.check_type, check.details);

        return (
          <div
            key={i}
            className={cn(
              "rounded-lg border bg-surface p-3",
              style.borderClassName,
            )}
          >
            <div className="flex items-center gap-2">
              <ResultIcon size={18} weight="fill" className={style.className} />
              <span className="text-sm font-medium text-foreground">
                {title}
              </span>
            </div>
            <span
              className={cn(
                "mt-1 block text-xs font-semibold",
                style.className,
              )}
            >
              {style.label}
            </span>
            {subtitle && (
              <p className="mt-1 text-xs text-muted">{subtitle}</p>
            )}
            {lines.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-foreground">
                {lines.map((line, j) => (
                  <li key={j}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
