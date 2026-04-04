export type TaskStatus =
  | "created"
  | "parsing"
  | "extracting"
  | "planning"
  | "awaiting_approval"
  | "generating"
  | "reviewing"
  | "revising"
  | "approved"
  | "exporting"
  | "completed"
  | "failed";

export type SectionStatus =
  | "draft"
  | "generating"
  | "generated"
  | "revising"
  | "approved";

export type ReviewSeverity = "critical" | "major" | "minor";
export type ReviewStatus = "pass" | "fail" | "pending";

export interface Task {
  id: string;
  title: string;
  doc_type: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: string;
  task_id: string;
  title: string;
  order_index: number;
  content: string | null;
  status: SectionStatus;
}

export interface ReviewIssue {
  id: string;
  section_id: string | null;
  reviewer_type: string;
  severity: ReviewSeverity;
  description: string;
  suggestion: string | null;
  excerpt: string | null;
}

export interface ReviewResult {
  id: string;
  task_id: string;
  reviewer_type: string;
  status: ReviewStatus;
  summary: string;
  issues: ReviewIssue[];
}
