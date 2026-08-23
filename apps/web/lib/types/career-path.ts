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

export type CareerPathDetail = CareerPath & {
  description_md: string;
  required_skills: CareerPathSkill[];
  related_career_paths: CareerPath[];
};

export type SkillCareerPathRef = {
  slug: string;
  title: string;
};

export type SkillDetail = Skill & {
  seo_summary: string | null;
  synonyms: string[] | null;
  related_skills: Skill[];
  career_paths: SkillCareerPathRef[];
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
