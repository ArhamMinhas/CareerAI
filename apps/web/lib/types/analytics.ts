export type SkillTrendPoint = {
  skill_id: string;
  skill_name: string;
  skill_slug: string;
  demand_count: number;
  growth_rate: number;
};

export type JobPostingTrendPoint = {
  period: string;
  total: number;
  remote: number;
  onsite: number;
};

export type SalaryTrendPoint = {
  period: string;
  average_p50: number;
};

export type TrendingCareerPath = {
  career_path_id: string;
  career_path_slug: string;
  career_path_title: string;
  growth_rate: number | null;
};

/** `GET /api/v1/analytics/market` (Phase 12) — catalog-wide, not personalized. */
export type MarketAnalytics = {
  top_growing_skills: SkillTrendPoint[];
  job_posting_trend: JobPostingTrendPoint[];
  salary_trend: SalaryTrendPoint[];
  trending_career_paths: TrendingCareerPath[];
};

export type SkillAnalyticsRow = {
  skill_id: string;
  skill_name: string;
  skill_slug: string;
  demand_count: number | null;
  growth_rate: number | null;
  avg_associated_salary: number | null;
};

/** `GET /api/v1/analytics/skills` (Phase 12) — the whole curated catalog, not one skill. */
export type SkillAnalytics = {
  rows: SkillAnalyticsRow[];
};

export type DashboardResumeSummary = {
  status: "uploaded" | "processing" | "completed" | "failed" | null;
  overall_score: number | null;
};

export type DashboardSkillGapSummary = {
  target_role: string;
  missing: number;
  weak: number;
  adequate: number;
  strong: number;
};

export type DashboardInterviewSummary = {
  total_completed: number;
  average_overall_score: number | null;
};

export type DashboardRoadmapSummary = {
  target_role: string;
  completed_items: number;
  total_items: number;
};

export type DashboardApplicationFunnel = {
  total_matches: number;
  saved: number;
  applied: number;
  interviewing: number;
  offer: number;
  rejected: number;
};

/** `GET /api/v1/analytics/dashboard` (Phase 12) — a real rollup of the current user's own
 * already-computed state. Each section is `null`/zeroed independently when that feature has no
 * data yet for this user. */
export type CandidateDashboard = {
  resume: DashboardResumeSummary;
  skill_gaps: DashboardSkillGapSummary | null;
  interviews: DashboardInterviewSummary;
  roadmap: DashboardRoadmapSummary | null;
  applications: DashboardApplicationFunnel;
};
