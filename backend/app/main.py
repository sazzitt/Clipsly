from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection, engine
from backend.app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application lifecycle: logging setup, DB validation, and graceful teardown."""
    # Startup sequence
    setup_logging()
    logger.info("Initializing %s v%s in %s mode...", settings.APP_NAME, settings.VERSION, settings.ENVIRONMENT)

    # Validate database connectivity and journal mode
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("Database connection initialized successfully (WAL mode verified).")
    else:
        logger.error("Database connection failed during startup initialization.")

    logger.info("Application ready and listening on http://%s:%d", settings.HOST, settings.PORT)

    yield

    # Shutdown sequence
    logger.info("Shutting down %s application cleanly...", settings.APP_NAME)
    await engine.dispose()
    logger.info("Database engine connections disposed.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Clipsly Local-First AI Video Clipper API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration strictly restricted to local Vite development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API v1 routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    """Root metadata ping."""
    return JSONResponse(
        content={
            "application": settings.APP_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/api/v1/system/health",
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
