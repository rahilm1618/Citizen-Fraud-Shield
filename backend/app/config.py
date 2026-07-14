"""
Application configuration — loaded from environment variables via .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Citizen Fraud Shield backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5434/citizen_fraud_shield"
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = "groq"  # "openai" | "gemini" | "groq"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    groq_api_key: str = ""
    hf_api_key: str = ""

    # ── JWT / Auth ────────────────────────────────────────────────────────
    jwt_secret: str = "cfs-dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440  # 24 hours

    # ── RAG ───────────────────────────────────────────────────────────────
    rag_similarity_threshold: float = 0.35

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
