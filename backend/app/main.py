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
            # Create all tables that don't already exist
            await conn.run_sync(Base.metadata.create_all)
        print("✅  Database tables created / verified")
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        sys.stderr.write(f"Database Connection Error: {e}\n")
        raise

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
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
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
