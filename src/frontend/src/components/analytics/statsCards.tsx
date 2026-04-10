import {
  PackageIcon,
  TrendUpIcon,
  TimerIcon,
  ClockIcon,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { AnalyticsData } from "@/types";
import { cn } from "@/utils/cn";

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function Card({
  title,
  value,
  icon: CardIcon,
  iconClassName,
}: {
  title: string;
  value: string | number;
  icon: Icon;
  iconClassName?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">
          {title}
        </p>
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            iconClassName ?? "bg-primary/10 text-primary"
          )}
        >
          <CardIcon size={18} weight="duotone" />
        </div>
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-foreground">
        {value}
      </p>
    </div>
  );
}

export function StatsCards({ data }: { data: AnalyticsData }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Card
        title="Total Processed"
        value={data.total_processed}
        icon={PackageIcon}
        iconClassName="bg-blue-100 text-blue-600"
      />
      <Card
        title="Approval Rate"
        value={`${(data.approval_rate * 100).toFixed(1)}%`}
        icon={TrendUpIcon}
        iconClassName="bg-green-100 text-green-600"
      />
      <Card
        title="Avg Processing"
        value={formatDuration(data.avg_processing_time_ms)}
        icon={TimerIcon}
        iconClassName="bg-purple-100 text-purple-600"
      />
      <Card
        title="Pending Review"
        value={data.by_status["PENDING_REVIEW"] ?? 0}
        icon={ClockIcon}
        iconClassName="bg-amber-100 text-amber-600"
      />
    </div>
  );
}
