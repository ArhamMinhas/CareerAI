from fastapi import APIRouter

from app.api.v1 import (
    applications,
    auth,
    career_goals,
    careers,
    companies,
    health,
    jobs,
    matches,
    profile,
    resumes,
    skills,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(career_goals.router)
api_router.include_router(skills.router)
api_router.include_router(careers.router)
api_router.include_router(resumes.router)
api_router.include_router(companies.router)
api_router.include_router(jobs.router)
api_router.include_router(matches.router)
api_router.include_router(applications.router)
