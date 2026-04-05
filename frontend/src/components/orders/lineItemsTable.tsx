import { PackageIcon } from "@phosphor-icons/react";
import type { LineItem } from "@/types";

function formatPrice(
  amount: number | null,
  currency: string | null,
): string {
  if (amount == null) return "\u2014";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "EUR",
  }).format(amount);
}

export function LineItemsTable({
  items,
  currency,
}: {
  items: LineItem[];
  currency: string | null;
}) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-muted">
        <PackageIcon size={32} weight="duotone" className="opacity-50" />
        <p className="text-sm">No line items.</p>
      </div>
    );
  }

  const total = items.reduce((sum, item) => {
    if (item.unit_price != null) {
      return sum + item.quantity * item.unit_price;
    }
    return sum;
  }, 0);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-xs font-semibold uppercase tracking-wider text-muted">
            <th className="px-4 py-2.5 text-left">Description</th>
            <th className="px-4 py-2.5 text-left">SKU</th>
            <th className="px-4 py-2.5 text-right">Qty</th>
            <th className="px-4 py-2.5 text-right">Unit Price</th>
            <th className="px-4 py-2.5 text-right">Subtotal</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((item, i) => (
            <tr key={i} className="transition-colors hover:bg-accent/50">
              <td className="px-4 py-2.5 text-foreground">{item.description}</td>
              <td className="px-4 py-2.5 font-mono text-xs text-muted">
                {item.sku ?? "\u2014"}
              </td>
              <td className="px-4 py-2.5 text-right text-foreground">{item.quantity}</td>
              <td className="px-4 py-2.5 text-right text-foreground">
                {formatPrice(item.unit_price, currency)}
              </td>
              <td className="px-4 py-2.5 text-right font-medium text-foreground">
                {item.unit_price != null
                  ? formatPrice(item.quantity * item.unit_price, currency)
                  : "\u2014"}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-border bg-surface-alt/50 font-semibold">
            <td colSpan={4} className="px-4 py-2.5 text-right text-foreground">
              Total
            </td>
            <td className="px-4 py-2.5 text-right text-foreground">
              {formatPrice(total, currency)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
