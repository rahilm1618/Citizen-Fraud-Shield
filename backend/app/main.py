"""
Citizen Fraud Shield — FastAPI Application Entry Point

Lifespan:
  - On startup: enables pgvector extension and creates all tables
  - On shutdown: disposes the engine connection pool

Endpoints (Step 1):
  - GET /health  →  basic health check
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine

# Import models so they register with Base.metadata
import app.models  # noqa: F401


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # ── Startup ───────────────────────────────────────────────────────────
    import sys
    import logging

    try:
        async with engine.begin() as conn:
            # Enable pgvector extension (idempotent)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # Note: We do NOT run Base.metadata.create_all here in production 
            # because DDL commands can hang indefinitely over a transaction pooler.
            # The tables were already created via the direct connection/seed script!
        print("✅  Database connected successfully")
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        sys.stderr.write(f"Database Connection Error: {e}\n")
        # We don't raise here so the server still boots and returns 500s rather than failing Render's port bind

    yield  # ← application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────
    await engine.dispose()
    print("🛑  Database connection pool disposed")


from app.routers import sessions, auth, admin, scam_patterns

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Citizen Fraud Shield",
    description="AI-powered scam detection and fraud network analysis for Indian citizens",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sessions.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(scam_patterns.router)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    """Basic health check — confirms the API is running."""
    return {
        "status": "healthy",
        "service": "citizen-fraud-shield",
        "version": "0.1.0",
    }

from fastapi.responses import JSONResponse
from fastapi import Request
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.error(f"Unhandled exception: {exc}")
    logging.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc), "traceback": traceback.format_exc()},
    )
