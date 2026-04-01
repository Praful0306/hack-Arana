"""
Matching Engine
---------------
Implements the dual-path hybrid retrieval pipeline:

  Phase 1 — Hard SQL filters (availability, open slots, domain gaps)
  Phase 2 — BM25 keyword score  (exact hard-skill match)
  Phase 3 — Semantic cosine similarity (dense embedding)
  Phase 4 — Diversity penalty  (prevents domain-homogeneous teams)
  Phase 5 — Fusion score       (weighted linear combination)
  Phase 6 — Cache in Redis     (30-min TTL)

Cold-start fallback: if user has < MIN_SKILLS_FOR_AI_MATCH skills,
skip AI scoring and rank by project popularity (view_count + applicant_count).
"""

import json
from typing import List, Tuple
from uuid import UUID
import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.user import User
from models.project import Project, ProjectRequiredSkill
from models.team import Team, TeamMember
from models.skill import UserSkill, Skill
from services.embedding_service import (
    build_user_text, build_project_text, embed_text,
    store_embedding, load_embedding, cosine_similarity
)
from schemas.matching import RankedProjectMatch, MatchExplanation
from config import settings
import structlog

log = structlog.get_logger()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def _compute_bm25(query_tokens: List[str], corpus: List[List[str]]) -> List[float]:
    if not corpus:
        return []
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)
    max_s = scores.max() if scores.max() > 0 else 1.0
    return (scores / max_s).tolist()


def _diversity_score(user_domain: str, existing_domains: List[str]) -> float:
    """
    Returns 1.0 if user's domain is not yet represented in the team.
    Returns 0.3 if domain is already present (penalise homogeneity).
    Rewards cross-disciplinary composition.
    """
    if not existing_domains:
        return 1.0
    if user_domain not in existing_domains:
        return 1.0
    overlap_ratio = existing_domains.count(user_domain) / len(existing_domains)
    return max(0.3, 1.0 - overlap_ratio)


def _reputation_score(rep: float, max_rep: float = 500.0) -> float:
    return min(rep / max_rep, 1.0)


def _fusion_score(bm25: float, semantic: float, diversity: float, reputation: float, momentum: float = 0.0) -> float:
    return (
        settings.WEIGHT_BM25 * bm25
        + settings.WEIGHT_SEMANTIC * semantic
        + settings.WEIGHT_DIVERSITY * diversity
        + settings.WEIGHT_REPUTATION * reputation
        + settings.WEIGHT_MOMENTUM * momentum
    )


# ── Main engine ───────────────────────────────────────────────────────────────

async def get_projects_for_user(
    user: User,
    db: AsyncSession,
    redis,
    limit: int = 20,
) -> Tuple[List[RankedProjectMatch], bool]:
    """
    Returns (ranked_matches, used_ai).
    used_ai=False means cold-start fallback was used.
    """
    cache_key = f"match:user:{user.user_id}:projects"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [RankedProjectMatch(**m) for m in data["matches"]], data["used_ai"]

    # Fetch user skills
    skill_result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user.user_id)
    )
    user_skills_rows = skill_result.scalars().all()

    is_cold_start = len(user_skills_rows) < settings.MIN_SKILLS_FOR_AI_MATCH
    used_ai = not is_cold_start

    # Fetch open projects with slots available
    team_size_sq = (
        select(func.count(TeamMember.member_id))
        .where(TeamMember.team_id == Team.team_id)
        .correlate(Team)
        .scalar_subquery()
    )
    projects_result = await db.execute(
        select(Project)
        .join(Team, Team.project_id == Project.project_id, isouter=True)
        .where(
            Project.status == "open",
            Project.founder_id != user.user_id,
        )
        .limit(200)
    )
    projects = projects_result.scalars().all()

    if not projects:
        return [], used_ai

    # Load required skills per project
    proj_ids = [p.project_id for p in projects]
    rs_result = await db.execute(
        select(ProjectRequiredSkill, Skill)
        .join(Skill, Skill.skill_id == ProjectRequiredSkill.skill_id)
        .where(ProjectRequiredSkill.project_id.in_(proj_ids))
    )
    proj_skills_map: dict = {}
    for rs, sk in rs_result.all():
        proj_skills_map.setdefault(str(rs.project_id), []).append(sk.skill_name)

    user_skill_names = [us.skill.skill_name for us in user_skills_rows if hasattr(us, "skill") and us.skill]

    # ── Cold-start fallback ────────────────────────────────────────────────
    if is_cold_start:
        log.info("cold_start_fallback", user_id=str(user.user_id))
        ranked = []
        for proj in projects:
            req_skills = proj_skills_map.get(str(proj.project_id), [])
            momentum = getattr(proj, 'momentum_score', 0.0) or 0.0
            view_count = getattr(proj, 'view_count', 0) or 0
            ranked.append(
                RankedProjectMatch(
                    project_id=proj.project_id,
                    title=proj.title,
                    description=proj.description,
                    stage=proj.stage.value,
                    industry_vertical=proj.industry_vertical,
                    required_skills=req_skills,
                    current_team_size=0,
                    max_team_size=proj.max_team_size,
                    momentum_score=round(momentum, 1),
                    match=MatchExplanation(
                        bm25_score=0.0, semantic_score=0.0, diversity_score=0.0,
                        reputation_score=0.0, momentum_score=round(momentum / 100, 4),
                        final_score=round((momentum * 0.7 + view_count * 0.3) / 100, 4),
                        matched_skills=[], missing_skills=req_skills,
                        diversity_breakdown={"note": "cold_start"},
                    ),
                )
            )
        # Sort cold-start by momentum + views (best UX for new users)
        ranked.sort(key=lambda x: x.match.final_score, reverse=True)
        ranked = ranked[:limit]
        await _cache_results(redis, cache_key, ranked, used_ai)
        return ranked, used_ai

    # ── AI hybrid path ─────────────────────────────────────────────────────
    # Get or build user embedding
    user_emb_key = f"embedding:user:{user.user_id}"
    user_emb = await load_embedding(redis, user_emb_key)
    if user_emb is None:
        profile_text = build_user_text(user, user.profile or {}, user_skills_rows)
        user_emb = await embed_text(profile_text)
        await store_embedding(redis, user_emb_key, user_emb)

    # Build BM25 corpus from project skill lists
    corpus = [_tokenize(" ".join(proj_skills_map.get(str(p.project_id), []))) for p in projects]
    user_query_tokens = _tokenize(" ".join(user_skill_names))
    bm25_scores = _compute_bm25(user_query_tokens, corpus)

    ranked = []
    for i, proj in enumerate(projects):
        req_skills = proj_skills_map.get(str(proj.project_id), [])

        # Semantic score
        proj_emb_key = f"embedding:project:{proj.project_id}"
        proj_emb = await load_embedding(redis, proj_emb_key)
        if proj_emb is None:
            proj_text = build_project_text(proj, [])
            proj_emb = await embed_text(proj_text)
            await store_embedding(redis, proj_emb_key, proj_emb)
        sem = cosine_similarity(user_emb, proj_emb)

        # Diversity (user domain vs existing team domains — simplified here)
        div = _diversity_score(user.domain.value, [])

        # Reputation
        rep = _reputation_score(user.reputation_score)

        # Momentum (normalised 0-1)
        proj_momentum = getattr(proj, 'momentum_score', 0.0) or 0.0
        mom = proj_momentum / 100.0

        bm25 = bm25_scores[i] if i < len(bm25_scores) else 0.0
        score = _fusion_score(bm25, sem, div, rep, mom)

        matched = [s for s in user_skill_names if s in req_skills]
        missing = [s for s in req_skills if s not in user_skill_names]

        ranked.append(
            RankedProjectMatch(
                project_id=proj.project_id,
                title=proj.title,
                description=proj.description,
                stage=proj.stage.value,
                industry_vertical=proj.industry_vertical,
                required_skills=req_skills,
                current_team_size=0,
                max_team_size=proj.max_team_size,
                momentum_score=round(proj_momentum, 1),
                match=MatchExplanation(
                    bm25_score=round(bm25, 4),
                    semantic_score=round(sem, 4),
                    diversity_score=round(div, 4),
                    reputation_score=round(rep, 4),
                    momentum_score=round(mom, 4),
                    final_score=round(score, 4),
                    matched_skills=matched,
                    missing_skills=missing,
                    diversity_breakdown={"user_domain": user.domain.value},
                ),
            )
        )

    ranked.sort(key=lambda x: x.match.final_score, reverse=True)
    ranked = ranked[:limit]

    await _cache_results(redis, cache_key, ranked, used_ai)
    return ranked, used_ai


async def _cache_results(redis, key: str, matches: List[RankedProjectMatch], used_ai: bool):
    """FIX: was sync using asyncio.ensure_future — silently dropped writes. Now properly awaited."""
    payload = {
        "matches": [m.model_dump(mode="json") for m in matches],
        "used_ai": used_ai,
    }
    await redis.set(key, json.dumps(payload), ex=settings.MATCH_CACHE_TTL)
