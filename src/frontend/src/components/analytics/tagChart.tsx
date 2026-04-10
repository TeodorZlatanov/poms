import type { TagCount } from "@/types";

function formatTag(tag: string): string {
  return tag
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function TagChart({ tags }: { tags: TagCount[] }) {
  const max = Math.max(...tags.map((t) => t.count), 1);

  if (tags.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">No tags.</p>;
  }

  return (
    <div className="space-y-3">
      {tags.map((tag) => (
        <div key={tag.tag}>
          <div className="mb-1.5 flex justify-between text-xs">
            <span className="font-medium text-foreground">
              {formatTag(tag.tag)}
            </span>
            <span className="font-semibold text-foreground">{tag.count}</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-accent">
            <div
              className="h-2.5 rounded-full bg-amber-500 transition-all duration-500"
              style={{ width: `${(tag.count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
