import {
  EnvelopeSimple,
  PaperPlaneTilt,
  Tray,
} from "@phosphor-icons/react";
import type { EmailRecord } from "@/types";
import { cn } from "@/utils/cn";

function formatEmailType(type: string): string {
  return type
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function EmailHistory({ emails }: { emails: EmailRecord[] }) {
  if (emails.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-6 text-muted">
        <EnvelopeSimple size={28} weight="duotone" className="opacity-50" />
        <p className="text-sm">No emails.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {emails.map((email, i) => {
        const isInbound = email.direction === "INBOUND";
        const DirectionIcon = isInbound ? Tray : PaperPlaneTilt;

        return (
          <div
            key={i}
            className="rounded-lg border border-border bg-surface p-3 transition-colors hover:bg-accent/30"
          >
            <div className="flex items-center gap-2">
              <DirectionIcon
                size={16}
                weight="duotone"
                className={cn(
                  isInbound ? "text-primary" : "text-green-600"
                )}
              />
              <span
                className={cn(
                  "text-xs font-semibold",
                  isInbound ? "text-primary" : "text-green-600"
                )}
              >
                {isInbound ? "Received" : "Sent"}
              </span>
              <span className="rounded bg-accent px-1.5 py-0.5 text-[11px] text-muted">
                {formatEmailType(email.email_type)}
              </span>
              <span className="ml-auto text-xs text-muted">
                {new Date(email.sent_at).toLocaleString()}
              </span>
            </div>
            <p className="mt-1.5 text-sm text-foreground">
              {isInbound ? "From" : "To"}:{" "}
              <span className="font-medium">
                {isInbound ? email.sender : email.recipient}
              </span>
            </p>
            {email.subject && (
              <p className="mt-0.5 text-xs text-muted">
                Subject: {email.subject}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
