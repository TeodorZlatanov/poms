import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitReview } from "@/api/reviews";
import type { ReviewRequest } from "@/types";

export function useSubmitReview(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: ReviewRequest) => submitReview(orderId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders", orderId] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
  });
}
