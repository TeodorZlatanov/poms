import {
  CheckCircle,
  XCircle,
  Warning,
  Question,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import type { ValidationCheck } from "@/types";
import { cn } from "@/utils/cn";

function formatCheckType(type: string): string {
  return type
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const resultStyles: Record<
  string,
  { icon: Icon; className: string; borderClassName: string }
> = {
  PASS: {
    icon: CheckCircle,
    className: "text-green-600 dark:text-green-400",
    borderClassName: "border-green-200 dark:border-green-800",
  },
  FAIL: {
    icon: XCircle,
    className: "text-red-600 dark:text-red-400",
    borderClassName: "border-red-200 dark:border-red-800",
  },
  WARNING: {
    icon: Warning,
    className: "text-amber-600 dark:text-amber-400",
    borderClassName: "border-amber-200 dark:border-amber-800",
  },
};

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
        };
        const ResultIcon = style.icon;

        return (
          <div
            key={i}
            className={cn(
              "rounded-lg border bg-surface p-3",
              style.borderClassName
            )}
          >
            <div className="flex items-center gap-2">
              <ResultIcon size={18} weight="fill" className={style.className} />
              <span className="text-sm font-medium text-foreground">
                {formatCheckType(check.check_type)}
              </span>
            </div>
            <span
              className={cn("mt-1 block text-xs font-semibold", style.className)}
            >
              {check.result}
            </span>
            {check.details && Object.keys(check.details).length > 0 && (
              <dl className="mt-2 space-y-1 text-xs">
                {Object.entries(check.details).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-muted">{key}</dt>
                    <dd className="text-foreground">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        );
      })}
    </div>
  );
}
