import { useQuery } from "@tanstack/react-query";
import { fetchOrders, fetchOrder } from "@/api/orders";
import type { OrderFilters } from "@/types";

export function useOrders(filters: OrderFilters = {}) {
  return useQuery({
    queryKey: ["orders", filters],
    queryFn: () => fetchOrders(filters),
    // Live dashboard — override the 5-min global staleTime and the disabled
    // focus refetch so placeholders and status transitions surface promptly.
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: true,
    // Poll fast (2s) while any order on the current page is still PROCESSING,
    // otherwise 3s so we reliably catch the brief processing window after a
    // new submission even before any row has flipped to PROCESSING yet.
    refetchInterval: (query) =>
      query.state.data?.items.some((o) => o.status === "PROCESSING")
        ? 2_000
        : 3_000,
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ["orders", id],
    queryFn: () => fetchOrder(id),
    enabled: !!id,
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: true,
    refetchInterval: (query) =>
      query.state.data?.status === "PROCESSING" ? 2_000 : 10_000,
  });
}
