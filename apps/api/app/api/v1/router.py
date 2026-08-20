from fastapi import APIRouter

from app.api.v1 import auth, career_goals, health, profile, resumes, skills

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(career_goals.router)
api_router.include_router(skills.router)
api_router.include_router(resumes.router)
