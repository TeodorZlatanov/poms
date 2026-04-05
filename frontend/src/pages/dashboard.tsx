import { useState } from "react";
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  CaretLeftIcon,
  CaretRightIcon,
  ClipboardTextIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  SpinnerIcon,
  WarningIcon,
} from "@phosphor-icons/react";
import { useOrders } from "@/hooks/useOrders";
import { OrderTable } from "@/components/orders/orderTable";
import { Select } from "@/components/ui/select";
import type { SelectOption } from "@/components/ui/select";
import { cn } from "@/utils/cn";
import type { OrderStatus } from "@/types";

const statusOptions: SelectOption<OrderStatus | "">[] = [
  { value: "", label: "All Statuses" },
  { value: "APPROVED", label: "Approved", icon: <CheckCircleIcon size={16} weight="fill" className="text-green-600" /> },
  { value: "PENDING_REVIEW", label: "Pending Review", icon: <ClockIcon size={16} weight="fill" className="text-amber-600" /> },
  { value: "REJECTED", label: "Rejected", icon: <XCircleIcon size={16} weight="fill" className="text-red-600" /> },
  { value: "PROCESSING", label: "Processing", icon: <SpinnerIcon size={16} weight="fill" className="text-blue-600" /> },
  { value: "FAILED", label: "Failed", icon: <WarningIcon size={16} weight="fill" className="text-gray-500" /> },
];

export function DashboardPage() {
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [vendor, setVendor] = useState("");
  const [vendorFilter, setVendorFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useOrders({
    status: status || undefined,
    vendor: vendorFilter || undefined,
    page,
    page_size: 20,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  function handleVendorKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      setVendorFilter(vendor);
      setPage(1);
    }
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <ClipboardTextIcon size={20} weight="duotone" className="text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Purchase Orders
          </h1>
          <p className="text-xs text-muted">
            Manage and review incoming purchase orders
          </p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Select
          value={status}
          onChange={(val) => {
            setStatus(val);
            setPage(1);
          }}
          options={statusOptions}
          placeholder="All Statuses"
          icon={
            <FunnelIcon size={16} weight="duotone" className="text-muted" />
          }
        />

        <div className="relative">
          <MagnifyingGlassIcon
            size={16}
            weight="duotone"
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            type="text"
            placeholder="Search vendor..."
            value={vendor}
            onChange={(e) => setVendor(e.target.value)}
            onKeyDown={handleVendorKeyDown}
            onBlur={() => {
              setVendorFilter(vendor);
              setPage(1);
            }}
            className={cn(
              "h-9 rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-foreground",
              "placeholder:text-muted",
              "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-1",
              "transition-shadow duration-150"
            )}
          />
        </div>
      </div>

      <div className="mt-5 overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center gap-3 py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-accent border-t-primary" />
            <p className="text-sm text-muted">Loading orders...</p>
          </div>
        ) : isError ? (
          <p className="py-16 text-center text-sm text-red-600">
            Failed to load orders. Check that the backend is running.
          </p>
        ) : data && data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-16">
            <ClipboardTextIcon
              size={40}
              weight="duotone"
              className="text-muted opacity-40"
            />
            <p className="text-sm font-medium text-foreground">
              No purchase orders found
            </p>
            <p className="text-xs text-muted">
              Submit a PO via the webhook or email to get started.
            </p>
          </div>
        ) : data ? (
          <OrderTable orders={data.items} />
        ) : null}
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs font-medium text-muted">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className={cn(
                "inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground",
                "transition-all duration-150",
                "hover:-translate-y-px hover:shadow-sm",
                "active:translate-y-0 active:scale-[0.97]",
                "disabled:pointer-events-none disabled:opacity-40"
              )}
            >
              <CaretLeftIcon size={14} />
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className={cn(
                "inline-flex h-8 items-center gap-1 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-foreground",
                "transition-all duration-150",
                "hover:-translate-y-px hover:shadow-sm",
                "active:translate-y-0 active:scale-[0.97]",
                "disabled:pointer-events-none disabled:opacity-40"
              )}
            >
              Next
              <CaretRightIcon size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
