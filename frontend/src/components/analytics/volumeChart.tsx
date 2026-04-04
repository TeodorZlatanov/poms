import type { DayVolume } from "@/types";
import { cn } from "@/utils/cn";

export function VolumeChart({ volume }: { volume: DayVolume[] }) {
  const max = Math.max(...volume.map((v) => v.count), 1);

  if (volume.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">No volume data.</p>;
  }

  return (
    <div className="flex items-end gap-1" style={{ height: "160px" }}>
      {volume.map((day) => (
        <div
          key={day.date}
          className="group relative flex flex-1 flex-col items-center justify-end"
          style={{ height: "100%" }}
        >
          <div
            className={cn(
              "w-full rounded-t-sm bg-primary transition-all duration-300",
              "group-hover:bg-primary-dark"
            )}
            style={{
              height: `${(day.count / max) * 100}%`,
              minHeight: day.count > 0 ? "4px" : "0px",
            }}
            title={`${day.date}: ${day.count}`}
          />
          <span className="mt-1 text-[10px] font-medium text-muted">
            {volume.length <= 14
              ? new Date(day.date + "T00:00:00").toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              : ""}
          </span>
        </div>
      ))}
    </div>
  );
}
