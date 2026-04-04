import { apiFetch } from "./client";
import type { AnalyticsData } from "@/types";
import { mockAnalytics } from "@/mocks/data";

export async function fetchAnalytics(): Promise<AnalyticsData> {
  try {
    return await apiFetch<AnalyticsData>("/analytics/");
  } catch {
    return mockAnalytics;
  }
}
