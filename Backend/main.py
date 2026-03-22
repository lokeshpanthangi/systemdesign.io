import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.chat_routes import chat
from routes.user_routes import user_router
from routes.problem_routes import problem_router
from routes.submission_routes import submission_router
from routes.session_routes import router as session_router
from routes.admin_routes import admin_router
from core.llm_provider import initialize_provider, get_provider

logger = logging.getLogger(__name__)

HEALTH_PING_INTERVAL = 4 * 60   # 4 minutes in seconds


async def _health_pinger():
    """Background task: hit /health every 4 minutes to keep the server warm."""
    import httpx
    await asyncio.sleep(HEALTH_PING_INTERVAL)   # wait before first ping
    while True:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get("http://127.0.0.1:8000/health", timeout=10)
            logger.info(f"[health-ping] {r.status_code}")
        except Exception as e:
            logger.warning(f"[health-ping] failed: {e}")
        await asyncio.sleep(HEALTH_PING_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initializes the LLM provider and health pinger."""
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("[startup] Initializing LLM provider...")
    result = initialize_provider()
    logger.info(f"[startup] LLM status: {result['status']} — {result['message']}")

    pinger = asyncio.create_task(_health_pinger())
    logger.info("[startup] Health pinger started (every 4 minutes)")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    pinger.cancel()
    provider = get_provider()
    if provider:
        provider.stop()
    logger.info("[shutdown] LLM provider stopped")


app = FastAPI(title="SystemDesign-io API", version="1.1.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(user_router)
app.include_router(problem_router)
app.include_router(submission_router)
app.include_router(session_router)
app.include_router(chat)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "Welcome to the SystemDesign.io API"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}