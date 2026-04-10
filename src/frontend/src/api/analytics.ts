import { apiFetch } from "./client";
import type { AnalyticsData } from "@/types";

export async function fetchAnalytics(): Promise<AnalyticsData> {
  return apiFetch<AnalyticsData>("/analytics/");
}
