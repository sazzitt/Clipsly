from fastapi import APIRouter
from backend.app.api.v1 import system

api_router = APIRouter(prefix="/api/v1")

# Register Module A: System & Health endpoints
api_router.include_router(system.router)
