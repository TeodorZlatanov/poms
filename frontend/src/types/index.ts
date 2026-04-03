export interface PurchaseOrder {
  id: string;
  po_number: string | null;
  vendor_name: string | null;
  total_amount: number | null;
  currency: string | null;
  status: OrderStatus;
  issue_tags: IssueTagSummary[];
  created_at: string;
}

export type OrderStatus =
  | "PROCESSING"
  | "APPROVED"
  | "PENDING_REVIEW"
  | "REJECTED"
  | "FAILED";

export interface IssueTagSummary {
  tag: string;
  severity: "SOFT" | "HARD";
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
