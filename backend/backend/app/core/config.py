from pathlib import Path

from pydantic_settings import BaseSettings

_HERE = Path(__file__).resolve().parent
_ENV_FILE = _HERE.parent.parent.parent / ".env"


class Settings(BaseSettings):
    app_name: str = "CrewLink AI"

    # ── Doc #6 §2 required secrets (fast-fail if empty) ────────────────
    llm_fast_api_key: str = ""
    llm_reasoning_api_key: str = ""
    llm_provider: str = ""
    database_url: str = "sqlite:///./crewlinai.db"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # ── App environment ────────────────────────────────────────────────
    environment: str = "development"

    # ── CrewLink-specific (backward-compat CREWLINK_ aliases) ──────────
    debug: bool = True
    chroma_persist_dir: str = "./chroma_data"
    venue_code: str = "founders_field"
    simulator_auth_token: str = "sim-service-token-change-in-prod"

    # ── CORS (comma-separated origins, or "*" for all) ──────────────────
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ── Thresholds (Doc #4 §2, ADDENDUM G8) ────────────────────────────
    min_grounding_similarity: float = 0.75
    classification_human_review_threshold: float = 0.6
    acknowledgment_sla_critical: int = 90
    acknowledgment_sla_standard: int = 240

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}

    def model_post_init(self, __context: object) -> None:
        """Fast-fail per Doc #6 §2 in production; allow empty in dev/test.

        In production (ENVIRONMENT=production) the app refuses to start with a
        missing required secret so a confusing mid-demo AI failure can't happen.
        In development/test the AI call sites gracefully fall back via
        LLM_MODE=recorded or the deterministic fallback chain (Doc #4 §5).
        """
        if self.environment != "production":
            return
        required = {
            "LLM_FAST_API_KEY": self.llm_fast_api_key,
            "LLM_REASONING_API_KEY": self.llm_reasoning_api_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            msg = (
                f"Missing required environment variables: {', '.join(missing)}. "
                "Set them in your platform's secrets manager. "
                "See .env.example for the full list."
            )
            raise ValueError(msg)


settings = Settings()
