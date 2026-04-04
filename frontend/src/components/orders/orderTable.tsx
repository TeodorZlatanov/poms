import { Link } from "react-router";
import { WarningDiamond, ArrowRight } from "@phosphor-icons/react";
import type { PurchaseOrder } from "@/types";
import { StatusBadge } from "@/components/orders/statusBadge";

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount == null) return "\u2014";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "EUR",
  }).format(amount);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString();
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
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {orders.map((order) => (
            <tr
              key={order.id}
              className="group transition-colors hover:bg-accent/50"
            >
              <td className="px-4 py-3">
                <Link
                  to={`/orders/${order.id}`}
                  className="font-medium text-primary hover:underline"
                >
                  {order.po_number ?? "\u2014"}
                </Link>
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
                    <WarningDiamond size={14} weight="fill" />
                    {order.issue_tags.length}
                  </span>
                ) : (
                  <span className="text-muted">\u2014</span>
                )}
              </td>
              <td className="px-4 py-3 text-muted">
                {formatDate(order.created_at)}
              </td>
              <td className="px-4 py-3">
                <Link
                  to={`/orders/${order.id}`}
                  className="text-muted opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <ArrowRight size={16} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
