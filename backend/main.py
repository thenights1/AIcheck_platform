"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import agent, auth, checkers, download, scan
from backend.config import get_config
from backend.logger import get_logger
from backend.registry import get_registry
from backend.store import get_task_store

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio as _asyncio
    from backend.api.agent import _set_main_loop
    _set_main_loop(_asyncio.get_running_loop())

    config = get_config()
    Path(config.storage.tasks_dir).mkdir(parents=True, exist_ok=True)
    get_task_store()
    registry = get_registry()
    logger.info("Loaded %d compliance skill(s): %s", len(registry), list(registry.keys()))
    logger.info("ComplianceAudit backend started on port %d", config.server.port)
    yield
    logger.info("ComplianceAudit backend shutting down")


app = FastAPI(
    title="ComplianceAudit",
    description="SKILL-driven compliance use-case audit system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(scan.router)
app.include_router(checkers.router)
app.include_router(agent.router)
app.include_router(agent.public_router)
app.include_router(download.router)

static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
