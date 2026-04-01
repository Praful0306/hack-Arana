"""
Embedding Service
-----------------
Generates dense vector embeddings for users and projects using OpenAI's
text-embedding-3-small model. Falls back to sentence-transformers (MiniLM)
when the OpenAI key is unavailable (local dev / cost savings).

Vectors are stored in Redis as JSON-serialized numpy arrays, keyed by:
  embedding:user:<user_id>
  embedding:project:<project_id>
"""

import json
import numpy as np
from typing import List, Optional
from openai import AsyncOpenAI
from config import settings
import structlog

log = structlog.get_logger()

_openai_client: Optional[AsyncOpenAI] = None
_local_model = None  # Lazy-loaded sentence-transformers model


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _local_model


async def embed_text(text: str) -> np.ndarray:
    """Return a unit-normalized embedding vector for the given text."""
    if settings.OPENAI_API_KEY:
        try:
            client = _get_openai()
            resp = await client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=text,
            )
            vec = np.array(resp.data[0].embedding, dtype=np.float32)
            return vec / np.linalg.norm(vec)
        except Exception as e:
            log.warning("OpenAI embedding failed, falling back to local model", error=str(e))

    # Local fallback
    model = _get_local_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype(np.float32)


def build_user_text(user, profile, skills: List) -> str:
    """Compose a rich text representation of a user for embedding."""
    skill_str = ", ".join(
        f"{us.skill.skill_name}(level={us.proficiency_level})" for us in skills
    )
    interests = profile.interests or ""
    bio = profile.bio or ""
    institution = profile.institution or ""
    return (
        f"Domain: {user.domain.value}\n"
        f"Institution: {institution}\n"
        f"Skills: {skill_str}\n"
        f"Interests: {interests}\n"
        f"Bio: {bio}"
    )


def build_project_text(project, required_skills: List) -> str:
    """Compose a rich text representation of a project for embedding."""
    skill_str = ", ".join(rs.skill.skill_name for rs in required_skills)
    return (
        f"Title: {project.title}\n"
        f"Problem: {project.problem_statement or ''}\n"
        f"Target Market: {project.target_market or ''}\n"
        f"Industry: {project.industry_vertical or ''}\n"
        f"Stage: {project.stage.value}\n"
        f"Required Skills: {skill_str}"
    )


async def store_embedding(redis, key: str, vec: np.ndarray) -> None:
    await redis.set(key, json.dumps(vec.tolist()), ex=86400 * 7)  # TTL 7 days


async def load_embedding(redis, key: str) -> Optional[np.ndarray]:
    data = await redis.get(key)
    if data is None:
        return None
    return np.array(json.loads(data), dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors must already be unit-normalized."""
    return float(np.dot(a, b))
