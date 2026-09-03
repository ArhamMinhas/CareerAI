"""Import every model here so `Base.metadata` is fully populated for Alembic autogenerate
(docs/DATABASE.md §5). Add new models to this list as they're introduced in later phases."""

from app.models.ai_conversation import AIConversation
from app.models.career_goal import CareerGoal
from app.models.career_path import CareerPath, CareerPathSkill
from app.models.company import Company
from app.models.education import Education
from app.models.embedding import Embedding
from app.models.experience import Experience
from app.models.job import Job, JobSkill
from app.models.job_match import Application, ApplicationStatus, JobMatch
from app.models.kb_chunk import KbChunk
from app.models.market_data import SalaryData, SkillDemand
from app.models.profile import Profile
from app.models.project import Project
from app.models.resource import Resource
from app.models.resume import FileType, Resume, ResumeStatus, ResumeVersion
from app.models.skill import Proficiency, Skill, SkillSource, UserSkill
from app.models.skill_gap import GapLevel, SkillGap
from app.models.user import Role, User

__all__ = [
    "AIConversation",
    "Application",
    "ApplicationStatus",
    "CareerGoal",
    "CareerPath",
    "CareerPathSkill",
    "Company",
    "Education",
    "Embedding",
    "Experience",
    "FileType",
    "GapLevel",
    "Job",
    "JobMatch",
    "JobSkill",
    "KbChunk",
    "Proficiency",
    "Profile",
    "Project",
    "Resource",
    "Resume",
    "ResumeStatus",
    "ResumeVersion",
    "Role",
    "SalaryData",
    "Skill",
    "SkillDemand",
    "SkillGap",
    "SkillSource",
    "User",
    "UserSkill",
]
