import {
  CheckCircle,
  XCircle,
  CircleNotch,
  Question,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { ProcessingLog } from "@/types";
import { cn } from "@/utils/cn";

function formatDuration(ms: number | null): string {
  if (ms == null) return "\u2014";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatStep(step: string): string {
  return step
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const statusConfig: Record<
  string,
  { icon: Icon; className: string }
> = {
  COMPLETED: { icon: CheckCircle, className: "text-green-500" },
  FAILED: { icon: XCircle, className: "text-red-500" },
  STARTED: { icon: CircleNotch, className: "text-primary" },
};

export function ProcessingTimeline({ logs }: { logs: ProcessingLog[] }) {
  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-muted">
        <Question size={28} weight="duotone" className="opacity-50" />
        <p className="text-sm">No processing logs.</p>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {logs.map((log, i) => {
        const config = statusConfig[log.status] ?? {
          icon: Question,
          className: "text-muted",
        };
        const StepIcon = config.icon;
        const isLast = i === logs.length - 1;

        return (
          <div key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={cn("flex-shrink-0", config.className)}>
                <StepIcon size={22} weight="fill" />
              </div>
              {!isLast && <div className="h-full w-px bg-border" />}
            </div>
            <div className="pb-4">
              <p className="text-sm font-medium text-foreground">
                {formatStep(log.step)}
              </p>
              <p className="text-xs text-muted">
                {formatDuration(log.duration_ms)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
