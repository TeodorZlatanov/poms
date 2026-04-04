import { useState } from "react";
import { CheckCircle, XCircle } from "@phosphor-icons/react";
import { useSubmitReview } from "@/hooks/useReview";
import type { OrderStatus } from "@/types";
import { cn } from "@/utils/cn";

export function ReviewPanel({
  orderId,
  status,
}: {
  orderId: string;
  status: OrderStatus;
}) {
  const [comment, setComment] = useState("");
  const mutation = useSubmitReview(orderId);

  if (status !== "PENDING_REVIEW" && status !== "REJECTED") {
    return null;
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-sm lg:col-span-2">
      <h3 className="text-sm font-semibold text-foreground">Review Decision</h3>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment..."
        rows={11}
        className={cn(
          "mt-3 max-h-64 w-full resize-none overflow-y-auto rounded-lg border border-border bg-surface-alt px-3 py-2 text-sm text-foreground",
          "placeholder:text-muted",
          "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-1",
          "transition-shadow duration-150"
        )}
      />

      <div className="mt-3 flex gap-2">
        <button
          onClick={() =>
            mutation.mutate({
              decision: "approve",
              comment: comment || undefined,
            })
          }
          disabled={mutation.isPending}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white",
            "bg-green-600 transition-all duration-150",
            "hover:-translate-y-px hover:bg-green-700",
            "active:translate-y-0 active:scale-[0.97]",
            "shadow-[0_1px_3px_rgba(0,0,0,0.12),0_0_0_0.5px_rgba(0,0,0,0.08)]",
            "hover:shadow-[0_2px_6px_rgba(0,0,0,0.16),0_0_0_0.5px_rgba(0,0,0,0.1)]",
            "disabled:pointer-events-none disabled:opacity-40"
          )}
        >
          <CheckCircle size={16} weight="fill" />
          {mutation.isPending ? "Submitting..." : "Approve"}
        </button>
        <button
          onClick={() =>
            mutation.mutate({
              decision: "reject",
              comment: comment || undefined,
            })
          }
          disabled={mutation.isPending}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white",
            "bg-red-600 transition-all duration-150",
            "hover:-translate-y-px hover:bg-red-700",
            "active:translate-y-0 active:scale-[0.97]",
            "shadow-[0_1px_3px_rgba(0,0,0,0.12),0_0_0_0.5px_rgba(0,0,0,0.08)]",
            "hover:shadow-[0_2px_6px_rgba(0,0,0,0.16),0_0_0_0.5px_rgba(0,0,0,0.1)]",
            "disabled:pointer-events-none disabled:opacity-40"
          )}
        >
          <XCircle size={16} weight="fill" />
          {mutation.isPending ? "Submitting..." : "Reject"}
        </button>
      </div>

      {mutation.isSuccess && (
        <p className="mt-2 flex items-center gap-1 text-sm text-green-600">
          <CheckCircle size={14} weight="fill" />
          Review submitted.
        </p>
      )}
      {mutation.isError && (
        <p className="mt-2 text-sm text-red-600">
          Failed to submit review. Please try again.
        </p>
      )}
    </div>
  );
}
