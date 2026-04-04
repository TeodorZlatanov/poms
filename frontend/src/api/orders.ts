import { apiFetch } from "./client";
import type { OrderListResponse, OrderDetail, OrderFilters } from "@/types";
import { getMockOrderList, mockOrderDetails } from "@/mocks/data";

export async function fetchOrders(
  filters: OrderFilters = {},
): Promise<OrderListResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.vendor) params.set("vendor", filters.vendor);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  const qs = params.toString();

  try {
    return await apiFetch<OrderListResponse>(`/orders/${qs ? `?${qs}` : ""}`);
  } catch {
    return getMockOrderList(filters);
  }
}

export async function fetchOrder(id: string): Promise<OrderDetail> {
  try {
    return await apiFetch<OrderDetail>(`/orders/${id}`);
  } catch {
    const mock = mockOrderDetails[id];
    if (mock) return mock;
    throw new Error("Order not found");
  }
}
