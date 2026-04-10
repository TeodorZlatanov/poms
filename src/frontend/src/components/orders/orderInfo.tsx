import {
  HashIcon,
  CalendarIcon,
  BuildingsIcon,
  UserIcon,
  CurrencyDollarIcon,
  TruckIcon,
  CreditCardIcon,
  FileIcon,
  EnvelopeIcon,
  ClockIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { OrderDetail } from "@/types";
import { StatusBadge } from "@/components/orders/statusBadge";

function formatAmount(amount: number | null, currency: string | null): string {
  if (amount == null) return "\u2014";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "EUR",
  }).format(amount);
}

function Field({
  label,
  value,
  icon: FieldIcon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: Icon;
}) {
  return (
    <div className="flex items-start gap-2.5">
      {FieldIcon && (
        <FieldIcon
          size={16}
          weight="duotone"
          className="mt-0.5 flex-shrink-0 text-muted"
        />
      )}
      <div className="min-w-0">
        <dt className="text-xs font-medium text-muted">{label}</dt>
        <dd className="mt-0.5 text-sm text-foreground">{value ?? "\u2014"}</dd>
      </div>
    </div>
  );
}

export function OrderInfo({ order }: { order: OrderDetail }) {
  return (
    <dl className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Field icon={HashIcon} label="PO Number" value={order.po_number} />
      <Field icon={CalendarIcon} label="PO Date" value={order.po_date} />
      <Field
        label="Status"
        value={<StatusBadge status={order.status} />}
      />
      <Field icon={BuildingsIcon} label="Vendor Name" value={order.vendor_name} />
      <Field icon={EnvelopeIcon} label="Vendor Contact" value={order.vendor_contact} />
      <Field icon={UserIcon} label="Requester" value={order.requester_name} />
      <Field icon={BuildingsIcon} label="Department" value={order.requester_department} />
      <Field
        icon={CurrencyDollarIcon}
        label="Total Amount"
        value={formatAmount(order.total_amount, order.currency)}
      />
      <Field icon={TruckIcon} label="Delivery Date" value={order.delivery_date} />
      <Field icon={CreditCardIcon} label="Payment Terms" value={order.payment_terms} />
      <Field icon={FileIcon} label="Original File" value={order.original_filename} />
      <Field icon={EnvelopeIcon} label="Sender Email" value={order.sender_email} />
      <Field
        icon={ClockIcon}
        label="Created"
        value={new Date(order.created_at).toLocaleString()}
      />
      <Field
        icon={ClockIcon}
        label="Updated"
        value={new Date(order.updated_at).toLocaleString()}
      />
    </dl>
  );
}
