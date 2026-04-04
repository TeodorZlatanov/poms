export type OrderStatus =
  | "PROCESSING"
  | "APPROVED"
  | "PENDING_REVIEW"
  | "REJECTED"
  | "FAILED";

// List view types
export interface PurchaseOrder {
  id: string;
  po_number: string | null;
  vendor_name: string | null;
  total_amount: number | null;
  currency: string | null;
  status: OrderStatus;
  issue_tags: string[];
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type OrderListResponse = PaginatedResponse<PurchaseOrder>;

// Detail view types
export interface ValidationCheck {
  check_type: string;
  result: string;
  details: Record<string, unknown> | null;
}

export interface IssueTag {
  tag: string;
  severity: "SOFT" | "HARD";
  description: string | null;
}

export interface EmailRecord {
  direction: string;
  email_type: string;
  sender: string;
  recipient: string;
  subject: string | null;
  sent_at: string;
}

export interface ProcessingLog {
  step: string;
  status: string;
  duration_ms: number | null;
}

export interface ReviewDecision {
  decision: string;
  comment: string | null;
  decided_at: string;
}

export interface LineItem {
  description: string;
  sku: string | null;
  quantity: number;
  unit_price: number | null;
}

export interface OrderDetail {
  id: string;
  po_number: string | null;
  po_date: string | null;
  vendor_name: string | null;
  vendor_contact: string | null;
  requester_name: string | null;
  requester_department: string | null;
  line_items: { items: LineItem[] } | null;
  total_amount: number | null;
  currency: string | null;
  delivery_date: string | null;
  payment_terms: string | null;
  status: OrderStatus;
  confidence_score: number | null;
  original_filename: string | null;
  sender_email: string | null;
  created_at: string;
  updated_at: string;
  validation_results: ValidationCheck[];
  issue_tags: IssueTag[];
  emails: EmailRecord[];
  processing_logs: ProcessingLog[];
  review: ReviewDecision | null;
}

// Review types
export interface ReviewRequest {
  decision: "approve" | "reject";
  comment?: string;
}

export interface ReviewResponse {
  id: string;
  order_id: string;
  decision: string;
  comment: string | null;
  decided_at: string;
  email_sent: boolean;
}

// Analytics types
export interface TagCount {
  tag: string;
  count: number;
}

export interface DayVolume {
  date: string;
  count: number;
}

export interface AnalyticsData {
  total_processed: number;
  by_status: Record<string, number>;
  approval_rate: number;
  common_tags: TagCount[];
  avg_processing_time_ms: number;
  volume_by_day: DayVolume[];
}

// Filter types
export interface OrderFilters {
  status?: OrderStatus;
  vendor?: string;
  page?: number;
  page_size?: number;
}
