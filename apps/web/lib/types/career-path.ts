import type { Skill } from "@/lib/types/profile";

export type CareerPath = {
  id: string;
  slug: string;
  title: string;
  summary: string;
  related_job_titles: string[] | null;
};

export type CareerPathSkill = {
  skill: Skill;
  weight: number;
  is_core: boolean;
};

/** Model 4's output (docs/ML_PIPELINE.md §3, Phase 8) — `null` when unavailable. */
export type PredictedSalaryRange = {
  p25: number;
  p50: number;
  p75: number;
  assumed_scope: string;
};

export type CareerPathDetail = CareerPath & {
  description_md: string;
  required_skills: CareerPathSkill[];
  related_career_paths: CareerPath[];
  predicted_salary_range: PredictedSalaryRange | null;
};

/** `GET /api/v1/career-recommendations` (docs/ML_PIPELINE.md §3 model 2, Phase 8) — ranked by
 * cosine similarity (the baseline), not the trained model — see the API route's docstring. */
export type CareerRecommendation = {
  career_path: CareerPath;
  fit_score: number;
};

export type SkillCareerPathRef = {
  slug: string;
  title: string;
};

/** One real weekly `skill_demand` observation (docs/ML_PIPELINE.md §3 model 6, Phase 8). */
export type SkillDemandPoint = {
  period: string;
  demand_count: number;
  growth_rate: number | null;
};

export type SkillDetail = Skill & {
  seo_summary: string | null;
  synonyms: string[] | null;
  related_skills: Skill[];
  career_paths: SkillCareerPathRef[];
  skill_family: string | null;
  demand_history: SkillDemandPoint[];
  demand_forecast: number | null;
};

export type GapLevel = "missing" | "weak" | "adequate" | "strong";

export type SkillGapItem = {
  skill: Skill;
  gap_level: GapLevel;
  priority: number;
};

export type SkillGapSummary = {
  missing: number;
  weak: number;
  adequate: number;
  strong: number;
};

export type SkillGapsResponse = {
  target_role: string;
  career_path: CareerPath;
  summary: SkillGapSummary;
  gaps: SkillGapItem[];
  recommended_next: SkillGapItem[];
};
