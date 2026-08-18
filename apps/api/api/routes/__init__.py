from fastapi import APIRouter

from apps.api.api.routes import (
    assets,
    auth,
    billing,
    director,
    jobs,
    members,
    projects,
    scripts,
    settings,
    templates,
    users,
    videos,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(members.router, tags=["members"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(scripts.router, prefix="/scripts", tags=["scripts"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(director.router, prefix="/director", tags=["director"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
