import { useQuery } from "@tanstack/react-query";
import { fetchOrders, fetchOrder } from "@/api/orders";
import type { OrderFilters } from "@/types";

export function useOrders(filters: OrderFilters = {}) {
  return useQuery({
    queryKey: ["orders", filters],
    queryFn: () => fetchOrders(filters),
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ["orders", id],
    queryFn: () => fetchOrder(id),
    enabled: !!id,
  });
}
