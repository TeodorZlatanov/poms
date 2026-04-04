import { ChartBar, ChartPie, Tag, CalendarBlank } from "@phosphor-icons/react";
import { useAnalytics } from "@/hooks/useAnalytics";
import { StatsCards } from "@/components/analytics/statsCards";
import { StatusChart } from "@/components/analytics/statusChart";
import { TagChart } from "@/components/analytics/tagChart";
import { VolumeChart } from "@/components/analytics/volumeChart";

export function AnalyticsPage() {
  const { data, isLoading, isError } = useAnalytics();

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <ChartBar size={20} weight="duotone" className="text-primary" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Analytics
          </h1>
        </div>
        <div className="mt-8 flex items-center justify-center py-16">
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-[3px] border-accent border-t-primary" />
            <p className="text-sm text-muted">Loading analytics...</p>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 lg:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <ChartBar size={20} weight="duotone" className="text-primary" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Analytics
          </h1>
        </div>
        <p className="mt-8 text-sm text-red-600">
          Failed to load analytics. Check that the backend is running.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <ChartBar size={20} weight="duotone" className="text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            Analytics
          </h1>
          <p className="text-xs text-muted">
            Overview of purchase order processing metrics
          </p>
        </div>
      </div>

      <div className="mt-6">
        <StatsCards data={data} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
        <section className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="flex items-center gap-2 border-b border-border px-5 py-3">
            <ChartPie size={16} weight="duotone" className="text-muted" />
            <h2 className="text-sm font-semibold text-foreground">
              Status Distribution
            </h2>
          </div>
          <div className="p-5">
            <StatusChart byStatus={data.by_status} />
          </div>
        </section>

        <section className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="flex items-center gap-2 border-b border-border px-5 py-3">
            <Tag size={16} weight="duotone" className="text-muted" />
            <h2 className="text-sm font-semibold text-foreground">
              Common Issue Tags
            </h2>
          </div>
          <div className="p-5">
            <TagChart tags={data.common_tags} />
          </div>
        </section>
      </div>

      <section className="mt-5 rounded-xl border border-border bg-surface shadow-sm">
        <div className="flex items-center gap-2 border-b border-border px-5 py-3">
          <CalendarBlank size={16} weight="duotone" className="text-muted" />
          <h2 className="text-sm font-semibold text-foreground">
            Volume by Day
          </h2>
        </div>
        <div className="p-5">
          <VolumeChart volume={data.volume_by_day} />
        </div>
      </section>
    </div>
  );
}
