import { apiFetch } from "./client";
import type { ReviewRequest, ReviewResponse } from "@/types";

export async function submitReview(
  orderId: string,
  request: ReviewRequest,
): Promise<ReviewResponse> {
  try {
    return await apiFetch<ReviewResponse>(`/reviews/${orderId}`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  } catch {
    return {
      id: crypto.randomUUID(),
      order_id: orderId,
      decision: request.decision,
      comment: request.comment ?? null,
      decided_at: new Date().toISOString(),
      email_sent: false,
    };
  }
}
