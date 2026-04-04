export type TaskStatus =
  | "created"
  | "parsing"
  | "extracting"
  | "planning"
  | "awaiting_outline_approval"
  | "generating"
  | "reviewing"
  | "awaiting_approval"
  | "approved"
  | "exporting"
  | "completed"
  | "failed";

export interface Task {
  id: string;
  name: string;
  doc_type: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: string;
  title: string;
  level: number;
  status: string;
  word_count: number;
  content?: string;
}

export interface ReviewIssue {
  id: string;
  severity: "critical" | "major" | "minor" | "info";
  description: string;
  section_id?: string;
  requires_human: boolean;
}

export interface ReviewResult {
  reviewer_name: string;
  status: "pass" | "fail" | "warning";
  score: number;
  issues: ReviewIssue[];
}

export interface AggregatedReview {
  overall_status: "approved" | "needs_revision" | "rejected";
  overall_score: number;
  reviewer_results: ReviewResult[];
  issues: ReviewIssue[];
  critical_count: number;
  major_count: number;
  minor_count: number;
  info_count: number;
}

export interface ApprovalState {
  status: "no_reviews" | "awaiting_approval" | "approved" | "changes_requested";
  review_summary?: AggregatedReview;
}

export interface SSEEvent {
  event: string;
  data: unknown;
  timestamp: string;
}
