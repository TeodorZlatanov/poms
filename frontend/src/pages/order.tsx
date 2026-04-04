import { Link, useParams } from "react-router";
import {
  ArrowLeft,
  Info,
  Tag,
  Package,
  ShieldCheck,
  EnvelopeSimple,
  Gavel,
} from "@phosphor-icons/react";
import { useOrder } from "@/hooks/useOrders";
import { StatusBadge } from "@/components/orders/statusBadge";
import { IssueTagPill } from "@/components/orders/issueTag";
import { OrderInfo } from "@/components/orders/orderInfo";
import { LineItemsTable } from "@/components/orders/lineItemsTable";
import { ValidationResults } from "@/components/orders/validationResults";
import { EmailHistory } from "@/components/orders/emailHistory";
import { ReviewPanel } from "@/components/reviews/reviewPanel";
import { cn } from "@/utils/cn";

function SectionCard({
  title,
  icon: SectionIcon,
  children,
  className,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border border-border bg-surface shadow-sm",
        className
      )}
    >
      <div className="flex items-center gap-2 border-b border-border px-5 py-3">
        <SectionIcon size={16} weight="duotone" className="text-muted" />
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function OrderPage() {
  const { id } = useParams();
  const { data: order, isLoading, isError } = useOrder(id ?? "");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-16">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-accent border-t-primary" />
          <p className="text-sm text-muted">Loading order...</p>
        </div>
      </div>
    );
  }

  if (isError || !order) {
    return (
      <div className="p-6 lg:p-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
        >
          <ArrowLeft size={14} />
          Back to Orders
        </Link>
        <p className="mt-4 text-sm text-red-600">Failed to load order.</p>
      </div>
    );
  }

  const lineItems = order.line_items?.items ?? [];

  return (
    <div className="p-6 lg:p-8">
      <div className="flex items-center justify-between">
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-primary transition-colors hover:text-primary-dark hover:underline"
        >
          <ArrowLeft size={14} />
          Back to Orders
        </Link>
        <StatusBadge status={order.status} />
      </div>

      <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
        {order.po_number ?? "Order Detail"}
      </h1>

      <SectionCard title="Order Information" icon={Info} className="mt-6">
        <OrderInfo order={order} />
      </SectionCard>

      {order.issue_tags.length > 0 && (
        <SectionCard title="Issue Tags" icon={Tag} className="mt-5">
          <div className="flex flex-wrap gap-2">
            {order.issue_tags.map((tag, i) => (
              <IssueTagPill
                key={i}
                tag={tag.tag}
                severity={tag.severity}
                description={tag.description}
              />
            ))}
          </div>
        </SectionCard>
      )}

      <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-5">
        <SectionCard
          title="Line Items"
          icon={Package}
          className="lg:col-span-3"
        >
          <LineItemsTable items={lineItems} currency={order.currency} />
        </SectionCard>

        <ReviewPanel orderId={order.id} status={order.status} />
      </div>

      <SectionCard
        title="Validation Results"
        icon={ShieldCheck}
        className="mt-5"
      >
        <ValidationResults checks={order.validation_results} />
      </SectionCard>

      <SectionCard title="Email History" icon={EnvelopeSimple} className="mt-5">
        <EmailHistory emails={order.emails} />
      </SectionCard>

      {order.review && (
        <SectionCard title="Review Decision" icon={Gavel} className="mt-5">
          <p className="text-sm text-foreground">
            <span className="font-semibold capitalize">
              {order.review.decision}
            </span>
            {order.review.comment && (
              <span className="text-muted"> &mdash; {order.review.comment}</span>
            )}
          </p>
          <p className="mt-1 text-xs text-muted">
            {new Date(order.review.decided_at).toLocaleString()}
          </p>
        </SectionCard>
      )}
    </div>
  );
}
