from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Antigravity"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    APP_ENV: str = "production"

    # Security
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/antigravity"
    DATABASE_URL_SYNC: str = "postgresql://postgres:password@localhost:5432/antigravity"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    MATCH_CACHE_TTL: int = 1800  # 30 min

    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o"
    EMBEDDING_DIMS: int = 1536

    # S3 / R2
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = "antigravity-uploads"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "auto"

    # Email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "team@antigravity.app"

    # OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Matching weights — must sum to 1.0
    WEIGHT_BM25: float = 0.30         # Hard skill keyword match
    WEIGHT_SEMANTIC: float = 0.30     # Dense vector cosine similarity
    WEIGHT_DIVERSITY: float = 0.20    # Cross-disciplinary bonus
    WEIGHT_REPUTATION: float = 0.10   # Past execution score
    WEIGHT_MOMENTUM: float = 0.10     # Project activity momentum

    # Cold-start threshold
    MIN_SKILLS_FOR_AI_MATCH: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
