export type FileType = "PDF" | "DOCX";
export type ResumeStatus = "uploaded" | "processing" | "completed" | "failed";

export type ResumeSummary = {
  id: string;
  file_name: string;
  file_type: FileType;
  status: ResumeStatus;
  overall_score: number | null;
  failure_reason: string | null;
  created_at: string;
};

export type SubScore = {
  score: number;
  explanation: string;
  evidence: string[];
};

export type ScoreBreakdown = {
  ats_compatibility: SubScore;
  skills: SubScore;
  experience: SubScore;
  projects: SubScore;
  education: SubScore;
  achievements: SubScore;
  keywords: SubScore;
  structure: SubScore;
};

export type ExtractedExperience = {
  company: string;
  title: string;
  start_date: string | null;
  end_date: string | null;
  description: string;
  bullets: string[];
};

export type ExtractedEducation = {
  institution: string;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
};

export type ExtractedProject = {
  title: string;
  description: string;
  url: string | null;
};

export type ResumeExtraction = {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  summary: string | null;
  skills: string[];
  experience: ExtractedExperience[];
  education: ExtractedEducation[];
  projects: ExtractedProject[];
  certifications: string[];
};

export type ResumeDetail = ResumeSummary & {
  structured_data: ResumeExtraction | null;
  score_breakdown: ScoreBreakdown | null;
  file_download_url: string | null;
};

export const SCORE_LABELS: Record<keyof ScoreBreakdown, string> = {
  ats_compatibility: "ATS compatibility",
  skills: "Skills",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
  achievements: "Achievements",
  keywords: "Keywords",
  structure: "Structure",
};
