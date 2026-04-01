from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user, get_redis
from models.user import User
from models.project import Project, ProjectRequiredSkill
from models.team import Team, TeamMember, MemberStatus
from models.skill import UserSkill, Skill
from services.matching_engine import get_projects_for_user
from schemas.matching import ProjectMatchResponse, UserMatchResponse, RankedUserMatch, MatchExplanation
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from services.embedding_service import (
    build_project_text, embed_text, load_embedding,
    store_embedding, cosine_similarity
)
from rank_bm25 import BM25Okapi
from config import settings

router = APIRouter(prefix="/match", tags=["Matching"])


@router.get("/projects", response_model=ProjectMatchResponse)
async def match_projects_for_me(
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Returns AI-ranked open projects for the current user.
    Falls back to popularity ranking if user has < 3 skills (cold start).
    """
    matches, used_ai = await get_projects_for_user(current_user, db, redis, limit=limit)
    return ProjectMatchResponse(matches=matches, total=len(matches), used_ai=used_ai)


@router.get("/users", response_model=UserMatchResponse)
async def match_users_for_project(
    project_id: UUID,
    limit: int = Query(20, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    """
    Returns AI-ranked candidate users for filling slots in a given project.
    Only the project founder or current team members can call this.
    """
    # Load project + required skills
    proj_result = await db.execute(
        select(Project)
        .options(selectinload(Project.required_skills).selectinload(ProjectRequiredSkill.skill))
        .where(Project.project_id == project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    req_skill_names = [rs.skill.skill_name for rs in project.required_skills if rs.skill]

    # Load current team domains (for diversity scoring)
    team_result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.project_id == project_id)
    )
    team = team_result.scalar_one_or_none()
    existing_domains = []
    existing_user_ids = set()
    if team:
        for m in team.members:
            if m.status == MemberStatus.active and m.user:
                existing_domains.append(m.user.domain.value)
                existing_user_ids.add(m.user_id)

    # Fetch candidate users (not already on team, not the founder)
    users_result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.skills).selectinload(UserSkill.skill),
        )
        .where(
            User.is_active == True,
            User.user_id.not_in(existing_user_ids),
            User.user_id != project.founder_id,
        )
        .limit(300)
    )
    candidates = users_result.scalars().all()

    if not candidates:
        return UserMatchResponse(matches=[], total=0, used_ai=False)

    # Get or build project embedding
    proj_emb_key = f"embedding:project:{project_id}"
    proj_emb = await load_embedding(redis, proj_emb_key)
    if proj_emb is None:
        proj_text = build_project_text(project, project.required_skills)
        proj_emb = await embed_text(proj_text)
        await store_embedding(redis, proj_emb_key, proj_emb)

    # BM25 corpus: each user's skill list
    def _tok(t): return t.lower().split()
    corpus = [
        _tok(" ".join(us.skill.skill_name for us in c.skills if us.skill))
        for c in candidates
    ]
    query_tokens = _tok(" ".join(req_skill_names))
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi(corpus) if corpus else None
    bm25_scores = bm25.get_scores(query_tokens) if bm25 else [0.0] * len(candidates)
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    bm25_norm = [s / max_bm25 for s in bm25_scores]

    ranked = []
    for i, candidate in enumerate(candidates):
        skill_names = [us.skill.skill_name for us in candidate.skills if us.skill]
        is_cold = len(skill_names) < settings.MIN_SKILLS_FOR_AI_MATCH

        # Semantic score
        if not is_cold:
            user_emb_key = f"embedding:user:{candidate.user_id}"
            user_emb = await load_embedding(redis, user_emb_key)
            if user_emb is None:
                sem = 0.5  # Unknown — give benefit of doubt
            else:
                sem = cosine_similarity(user_emb, proj_emb)
        else:
            sem = 0.3  # Cold-start penalty

        bm25_s = bm25_norm[i]

        # Diversity bonus
        dom = candidate.domain.value
        if dom not in existing_domains:
            div = 1.0
        else:
            count = existing_domains.count(dom)
            div = max(0.3, 1.0 - (count / max(len(existing_domains), 1)))

        rep = min(candidate.reputation_score / 500.0, 1.0)
        final = (
            settings.WEIGHT_BM25 * bm25_s
            + settings.WEIGHT_SEMANTIC * sem
            + settings.WEIGHT_DIVERSITY * div
            + settings.WEIGHT_REPUTATION * rep
        )

        matched = [s for s in skill_names if s in req_skill_names]
        missing = [s for s in req_skill_names if s not in skill_names]

        ranked.append(RankedUserMatch(
            user_id=candidate.user_id,
            full_name=candidate.full_name,
            domain=candidate.domain.value,
            skills=skill_names,
            reputation_score=candidate.reputation_score,
            availability_hours=candidate.profile.availability_hours if candidate.profile else 0,
            match=MatchExplanation(
                bm25_score=round(bm25_s, 4),
                semantic_score=round(sem, 4),
                diversity_score=round(div, 4),
                reputation_score=round(rep, 4),
                final_score=round(final, 4),
                matched_skills=matched,
                missing_skills=missing,
                diversity_breakdown={"user_domain": dom, "existing_domains": existing_domains},
            ),
        ))

    ranked.sort(key=lambda x: x.match.final_score, reverse=True)
    ranked = ranked[:limit]
    return UserMatchResponse(matches=ranked, total=len(ranked), used_ai=True)


@router.delete("/cache/me")
async def invalidate_my_match_cache(
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """Manually bust the match cache for the current user (e.g., after profile update)."""
    key = f"match:user:{current_user.user_id}:projects"
    await redis.delete(key)
    return {"detail": "Match cache cleared"}
