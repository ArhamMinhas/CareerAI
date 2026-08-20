export type Profile = {
  id: string;
  user_id: string;
  full_name: string | null;
  headline: string | null;
  location: string | null;
  avatar_url: string | null;
  bio: string | null;
};

export type Education = {
  id: string;
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
};

export type Experience = {
  id: string;
  company: string;
  title: string;
  location: string | null;
  employment_type: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
};

export type Project = {
  id: string;
  title: string;
  description: string | null;
  url: string | null;
  repo_url: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type Proficiency = "beginner" | "intermediate" | "advanced" | "expert";

export type UserSkill = {
  id: string;
  skill_id: string;
  name: string;
  category: string | null;
  proficiency: Proficiency;
  source: "resume" | "manual" | "interview";
};

export type Skill = {
  id: string;
  name: string;
  slug: string;
  category: string | null;
};

export type CareerGoal = {
  id: string;
  target_role: string;
  target_industry: string | null;
  target_years_experience: number | null;
  is_active: boolean;
};
