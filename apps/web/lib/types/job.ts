import type { Skill } from "@/lib/types/profile";

export type Company = {
  id: string;
  name: string;
  slug: string;
  industry: string | null;
  logo_url: string | null;
  description: string | null;
};

export type Job = {
  id: string;
  title: string;
  company: Company;
  seniority_level: string | null;
  employment_type: string | null;
  location: string | null;
  remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  posted_at: string;
};

export type JobSkill = {
  skill: Skill;
  is_required: boolean;
  weight: number;
};

export type JobDetail = Job & {
  description: string;
  required_skills: JobSkill[];
};

export type CompanyDetail = Company & {
  jobs: Job[];
};

export type JobMatchSubScore = {
  score: number;
  weight: number;
  explanation: string;
};

export type JobMatchBreakdown = {
  semantic_similarity: JobMatchSubScore;
  skill_overlap: JobMatchSubScore;
  experience_match: JobMatchSubScore;
  education_match: JobMatchSubScore;
  preference_match: JobMatchSubScore;
  location_match: JobMatchSubScore;
};

export type JobMatch = {
  id: string;
  job: Job;
  match_score: number;
  score_breakdown: JobMatchBreakdown;
  explanation: string;
};

export type ApplicationStatus = "saved" | "applied" | "interviewing" | "offer" | "rejected";

export type Application = {
  id: string;
  job: Job;
  status: ApplicationStatus;
  applied_at: string | null;
  created_at: string;
};

export type ApplicationsResponse = {
  applications: Application[];
};
