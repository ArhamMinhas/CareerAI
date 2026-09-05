from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    applications,
    auth,
    career_goals,
    career_recommendations,
    careers,
    companies,
    health,
    interviews,
    jobs,
    learning_roadmap,
    matches,
    profile,
    rag,
    resources,
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
api_router.include_router(career_recommendations.router)
api_router.include_router(resumes.router)
api_router.include_router(companies.router)
api_router.include_router(jobs.router)
api_router.include_router(matches.router)
api_router.include_router(applications.router)
api_router.include_router(resources.router)
api_router.include_router(rag.router)
api_router.include_router(learning_roadmap.router)
api_router.include_router(interviews.router)
api_router.include_router(analytics.router)
