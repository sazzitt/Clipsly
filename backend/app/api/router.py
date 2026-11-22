from fastapi import APIRouter
from backend.app.api.v1 import clips, exports, highlights, jobs, system, transcripts, videos

api_router = APIRouter(prefix="/api/v1")

# Mount all domain routers under /api/v1
api_router.include_router(system.router)
api_router.include_router(videos.router)
api_router.include_router(jobs.router)
api_router.include_router(transcripts.router)
api_router.include_router(highlights.router)
api_router.include_router(clips.router)
api_router.include_router(exports.router)
