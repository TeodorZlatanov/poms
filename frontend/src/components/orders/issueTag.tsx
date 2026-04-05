import { WarningOctagonIcon, WarningCircleIcon } from "@phosphor-icons/react";
import { cn } from "@/utils/cn";

function formatTagName(tag: string): string {
  return tag
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function IssueTagPill({
  tag,
  severity,
  description,
}: {
  tag: string;
  severity: "SOFT" | "HARD";
  description?: string | null;
}) {
  const isHard = severity === "HARD";
  const Icon = isHard ? WarningOctagonIcon : WarningCircleIcon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        isHard ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
      )}
      title={description ?? undefined}
    >
      <Icon size={14} weight="fill" />
      {formatTagName(tag)}
    </span>
  );
}
