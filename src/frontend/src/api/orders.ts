import { apiFetch } from "./client";
import type { OrderListResponse, OrderDetail, OrderFilters } from "@/types";

export async function fetchOrders(
  filters: OrderFilters = {},
): Promise<OrderListResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.vendor) params.set("vendor", filters.vendor);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const qs = params.toString();

  return apiFetch<OrderListResponse>(`/orders/${qs ? `?${qs}` : ""}`);
}

export async function fetchOrder(id: string): Promise<OrderDetail> {
  return apiFetch<OrderDetail>(`/orders/${id}`);
}
