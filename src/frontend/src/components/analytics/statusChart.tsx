const statusColors: Record<string, string> = {
  APPROVED: "bg-green-500",
  PENDING_REVIEW: "bg-amber-500",
  REJECTED: "bg-red-500",
  PROCESSING: "bg-blue-500",
  FAILED: "bg-gray-400",
};

function formatStatus(status: string): string {
  return status
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function StatusChart({
  byStatus,
}: {
  byStatus: Record<string, number>;
}) {
  const entries = Object.entries(byStatus);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  if (entries.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">No data.</p>;
  }

  return (
    <div className="space-y-3">
      {entries.map(([status, count]) => (
        <div key={status}>
          <div className="mb-1.5 flex justify-between text-xs">
            <span className="font-medium text-foreground">
              {formatStatus(status)}
            </span>
            <span className="font-semibold text-foreground">{count}</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-accent">
            <div
              className={`h-2.5 rounded-full transition-all duration-500 ${statusColors[status] ?? "bg-gray-400"}`}
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
