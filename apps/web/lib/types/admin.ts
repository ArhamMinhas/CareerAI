export type Role = "USER" | "ADMIN" | "RECRUITER";

export type AdminUser = {
  id: string;
  email: string;
  role: Role;
  email_verified: boolean;
  created_at: string;
};

export type AdminCompanyRef = {
  id: string;
  name: string;
  slug: string;
};

export type AdminJob = {
  id: string;
  title: string;
  company: AdminCompanyRef;
  is_active: boolean;
  remote: boolean;
  source: string | null;
  search_category: string | null;
  created_at: string;
};

export type AdminJobCreateRequest = {
  company_id: string;
  title: string;
  description: string;
  seniority_level?: string | null;
  employment_type?: string | null;
  location?: string | null;
  remote?: boolean;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string | null;
  apply_url?: string | null;
  search_category?: string | null;
  required_skill_names?: string[];
};

export type AdminSkill = {
  id: string;
  name: string;
  slug: string;
  category: string | null;
  has_curated_content: boolean;
  created_at: string;
};

export type AIUsageByFeature = {
  feature: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  avg_latency_ms: number;
};

export type AIUsageByModel = {
  model: string;
  call_count: number;
  prompt_tokens: number;
  completion_tokens: number;
  avg_latency_ms: number;
};

/** `GET /api/v1/admin/ai-usage` — real aggregates over `ai_conversations` (Phase 5). No dollar
 * cost: no real pricing constants exist anywhere in the backend. */
export type AIUsage = {
  by_feature: AIUsageByFeature[];
  by_model: AIUsageByModel[];
};

export type ModelMetricsEntry = {
  name: string;
  version: string;
  available: boolean;
  metric: string | null;
  score: number | null;
  training_window: string | null;
  limitations: string | null;
  retrained_at: string | null;
};

/** `GET /api/v1/admin/model-metrics` — real stored per-model metadata (Phase 8), never a live
 * drift computation (Phase 14 scope). `available: false` for a model whose metadata is missing
 * or malformed. */
export type ModelMetrics = {
  models: ModelMetricsEntry[];
};

/** `GET /api/v1/admin/system-health` — real DB/Redis connectivity + key-table counts, not
 * audit-log-based (Phase 15 scope). */
export type SystemHealth = {
  database_ok: boolean;
  redis_ok: boolean;
  total_users: number;
  total_jobs: number;
  total_resumes: number;
};
