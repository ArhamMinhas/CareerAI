"""Import every model here so `Base.metadata` is fully populated for Alembic autogenerate
(docs/DATABASE.md §5). Add new models to this list as they're introduced in later phases."""

from app.models.career_goal import CareerGoal
from app.models.education import Education
from app.models.experience import Experience
from app.models.profile import Profile
from app.models.project import Project
from app.models.resume import FileType, Resume, ResumeStatus, ResumeVersion
from app.models.skill import Proficiency, Skill, SkillSource, UserSkill
from app.models.user import Role, User

__all__ = [
    "CareerGoal",
    "Education",
    "Experience",
    "FileType",
    "Proficiency",
    "Profile",
    "Project",
    "Resume",
    "ResumeStatus",
    "ResumeVersion",
    "Role",
    "Skill",
    "SkillSource",
    "User",
    "UserSkill",
]
