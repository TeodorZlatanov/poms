import {
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  SpinnerIcon,
  WarningIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { OrderStatus } from "@/types";
import { cn } from "@/utils/cn";

const statusConfig: Record<
  OrderStatus,
  { label: string; className: string; icon: Icon }
> = {
  APPROVED: {
    label: "Approved",
    className: "bg-green-100 text-green-800",
    icon: CheckCircleIcon,
  },
  PENDING_REVIEW: {
    label: "Pending Review",
    className: "bg-amber-100 text-amber-800",
    icon: ClockIcon,
  },
  REJECTED: {
    label: "Rejected",
    className: "bg-red-100 text-red-800",
    icon: XCircleIcon,
  },
  PROCESSING: {
    label: "Processing",
    className: "bg-blue-100 text-blue-800",
    icon: SpinnerIcon,
  },
  FAILED: {
    label: "Failed",
    className: "bg-gray-100 text-gray-700",
    icon: WarningIcon,
  },
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  const config = statusConfig[status] ?? {
    label: status,
    className: "bg-gray-100 text-gray-700",
    icon: WarningIcon,
  };

  const StatusIcon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        config.className
      )}
    >
      <StatusIcon size={14} weight="fill" />
      {config.label}
    </span>
  );
}
