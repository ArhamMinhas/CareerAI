import type { CareerPath } from "@/lib/types/career-path";
import type { Skill } from "@/lib/types/profile";

export type RoadmapPhase = "foundations" | "core" | "advanced";
export type LearningPathStatus = "active" | "completed" | "abandoned";
export type LearningResourceType = "course" | "article" | "project" | "docs";

export type SkillLearningResource = {
  id: string;
  title: string;
  url: string | null;
  resource_type: LearningResourceType;
  estimated_hours: number | null;
  /** Set when this resource links to a curated /resources/[slug] article (Phase 9) rather than
   * an external url. */
  resource_slug: string | null;
};

export type LearningPathItem = {
  id: string;
  skill: Skill;
  phase: RoadmapPhase;
  order_index: number;
  completed: boolean;
  completed_at: string | null;
  resources: SkillLearningResource[];
};

export type LearningRoadmapProgress = {
  completed: number;
  total: number;
};

/** `GET/POST /api/v1/learning-roadmap*` (docs/API.md §5, Phase 10) — backs `/dashboard/roadmap`. */
export type LearningRoadmap = {
  id: string;
  target_role: string;
  career_path: CareerPath;
  overview: string | null;
  status: LearningPathStatus;
  generated_at: string | null;
  items: LearningPathItem[];
  progress: LearningRoadmapProgress;
};
