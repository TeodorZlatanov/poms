import { Link } from "react-router";
import { WarningDiamondIcon, ArrowRightIcon } from "@phosphor-icons/react";
import type { PurchaseOrder } from "@/types";
import { StatusBadge } from "@/components/orders/statusBadge";

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount == null) return "\u2014";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "EUR",
  }).format(amount);
}

// Backend serializes timestamps as naïve UTC (no tz suffix). Appending "Z"
// forces JS to parse them as UTC so toLocale* then converts to browser time.
function parseUtc(iso: string): Date {
  return new Date(/[Z+]|-\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`);
}

function formatDate(iso: string): string {
  return parseUtc(iso).toLocaleDateString();
}

function formatTime(iso: string): string {
  return parseUtc(iso).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function OrderTable({ orders }: { orders: PurchaseOrder[] }) {
  if (orders.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted">
        No purchase orders found.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-surface-alt/50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              PO Number
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Vendor
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Amount
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Issues
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Date
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted">
              Time
            </th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {orders.map((order) => {
            const isProcessing = order.status === "PROCESSING";
            return (
              <tr
                key={order.id}
                className={
                  isProcessing
                    ? "group cursor-not-allowed opacity-70"
                    : "group transition-colors hover:bg-accent/50"
                }
              >
                <td className="px-4 py-3">
                  {isProcessing ? (
                    <span className="font-medium text-muted">
                      {order.po_number ?? "\u2014"}
                    </span>
                  ) : (
                    <Link
                      to={`/orders/${order.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {order.po_number ?? "\u2014"}
                    </Link>
                  )}
                </td>
                <td className="px-4 py-3 text-foreground">
                  {order.vendor_name ?? "\u2014"}
                </td>
                <td className="px-4 py-3 font-medium text-foreground">
                  {formatAmount(order.total_amount, order.currency)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={order.status} />
                </td>
                <td className="px-4 py-3">
                  {order.issue_tags.length > 0 ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-800">
                      <WarningDiamondIcon size={14} weight="fill" />
                      {order.issue_tags.length}
                    </span>
                  ) : (
                    <span className="text-muted">{"\u2014"}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-muted">
                  {formatDate(order.created_at)}
                </td>
                <td className="px-4 py-3 text-muted tabular-nums">
                  {formatTime(order.created_at)}
                </td>
                <td className="px-4 py-3">
                  {!isProcessing && (
                    <Link
                      to={`/orders/${order.id}`}
                      className="text-muted opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <ArrowRightIcon size={16} />
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
