export type InterviewMode =
  | "technical"
  | "behavioral"
  | "hr"
  | "system_design"
  | "ml"
  | "data_science";

export type InterviewStatus = "in_progress" | "completed" | "abandoned";

export const INTERVIEW_MODE_LABELS: Record<InterviewMode, string> = {
  technical: "Technical",
  behavioral: "Behavioral",
  hr: "HR",
  system_design: "System Design",
  ml: "Machine Learning",
  data_science: "Data Science",
};

export type InterviewEvaluation = {
  correctness_score: number;
  depth_score: number;
  communication_score: number;
  feedback: string;
};

export type InterviewAnswer = {
  answer_text: string;
  response_time_seconds: number;
  created_at: string;
  evaluation: InterviewEvaluation | null;
};

export type InterviewQuestion = {
  id: string;
  question_text: string;
  category: string;
  order_index: number;
  answer: InterviewAnswer | null;
};

/** List-view projection — `GET /api/v1/interviews` (history). */
export type Interview = {
  id: string;
  mode: InterviewMode;
  target_role: string | null;
  status: InterviewStatus;
  overall_score: number | null;
  created_at: string;
};

/** `POST /api/v1/interviews`, `GET /api/v1/interviews/{id}`, `POST .../answer` — every route
 * that returns a full session, including every question asked so far with its answer/evaluation
 * if already submitted. The "current question" is derived client-side as the first item with
 * `answer === null` (docs/API.md §5, Phase 11). */
export type InterviewDetail = Interview & {
  questions: InterviewQuestion[];
};

export type InterviewAnalyticsRecent = {
  interview_id: string;
  mode: InterviewMode;
  overall_score: number;
  completed_at: string;
};

/** `GET /api/v1/interviews/analytics` — real aggregates over the user's own completed sessions
 * only. All averages `null`/`recent` empty when the user has no completed interviews yet. */
export type InterviewAnalytics = {
  total_completed: number;
  average_overall_score: number | null;
  average_correctness_score: number | null;
  average_depth_score: number | null;
  average_communication_score: number | null;
  recent: InterviewAnalyticsRecent[];
};
