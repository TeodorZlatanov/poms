import { apiFetch } from "./client";
import type { ReviewRequest, ReviewResponse } from "@/types";

export async function submitReview(
  orderId: string,
  request: ReviewRequest,
): Promise<ReviewResponse> {
  return apiFetch<ReviewResponse>(`/reviews/${orderId}`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
