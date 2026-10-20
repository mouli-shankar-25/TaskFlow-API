from fastapi import APIRouter

from app.api.v1.endpoints import auth, memberships, projects, tasks, users

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(memberships.router)
api_v1_router.include_router(tasks.router)
