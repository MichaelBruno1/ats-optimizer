"""FastAPI application entry point for ATS Optimizer.

Configures:
- CORS middleware
- API router (prefix: /api/v1)
- Static frontend serving (Docker: /app/static, dev: ../../frontend)
- Lifespan context (temp directory creation + background cleanup task)
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.config import settings
from app.services.temp_storage import cleanup_old_sessions

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup + graceful shutdown.

    On startup:
    - Creates the temporary storage directory if it does not exist.
    - Starts the background session cleanup task.

    On shutdown:
    - Cancels the cleanup background task cleanly.
    """
    # Startup ─────────────────────────────────────────────────────────────────
    temp_path = Path(settings.temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    logger.info("Temporary storage directory: %s", temp_path)

    cleanup_task = asyncio.create_task(
        cleanup_old_sessions(), name="session-cleanup"
    )
    logger.info(
        "Background cleanup task started (interval: %d min)",
        settings.temp_cleanup_minutes,
    )

    logger.info(
        "ATS Optimizer backend started — LLM: %s/%s",
        settings.llm_provider,
        settings.llm_model,
    )

    yield  # Application is running

    # Shutdown ────────────────────────────────────────────────────────────────
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("ATS Optimizer backend shut down cleanly.")


# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="ATS Optimizer API",
    description=(
        "AI-powered resume optimization service that analyzes job descriptions "
        "and tailors resumes for maximum ATS compatibility."
    ),
    version="1.0.5",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API router ────────────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")

# ── Static frontend ───────────────────────────────────────────────────────────
# Priority 1: Docker container path (/app/static)
_docker_static = Path("/app/static")
# Priority 2: Local development path (relative to backend/app/main.py)
_dev_frontend = Path(__file__).parent.parent.parent / "frontend"

if _docker_static.is_dir():
    app.mount("/", StaticFiles(directory=str(_docker_static), html=True), name="static")
    logger.info("Serving frontend from Docker path: %s", _docker_static)
elif _dev_frontend.is_dir():
    app.mount("/", StaticFiles(directory=str(_dev_frontend), html=True), name="static")
    logger.info("Serving frontend from dev path: %s", _dev_frontend)
else:
    logger.warning(
        "No frontend directory found at '%s' or '%s'. "
        "API is functional but no UI will be served.",
        _docker_static,
        _dev_frontend,
    )
