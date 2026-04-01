from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.project import Project
from models.team import Team, TeamMember, MemberStatus
from models.milestone import Milestone, MilestoneStatus
from services import ai_service, storage_service

router = APIRouter(prefix="/ai", tags=["AI Tools"])


async def _get_project_context(project_id: UUID, db: AsyncSession):
    """Helper: loads project + team + milestones into plain dicts."""
    proj_result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    team_result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.project_id == project_id)
    )
    team = team_result.scalar_one_or_none()

    milestones_result = await db.execute(
        select(Milestone).where(Milestone.project_id == project_id)
    )
    milestones = milestones_result.scalars().all()

    project_data = {
        "title": project.title,
        "description": project.description,
        "problem_statement": project.problem_statement,
        "target_market": project.target_market,
        "industry_vertical": project.industry_vertical,
        "stage": project.stage.value,
    }
    team_data = {
        "members": [
            {"name": m.user.full_name, "domain": m.user.domain.value}
            for m in (team.members if team else [])
            if m.status == MemberStatus.active and m.user
        ]
    }
    milestone_list = [
        {"title": m.title, "status": m.status.value, "due_date": str(m.due_date)}
        for m in milestones
    ]
    return project_data, team_data, milestone_list


def _assert_team_member_sync(team, user_id):
    if not team:
        raise HTTPException(status_code=403, detail="No team found for this project")
    member_ids = {m.user_id for m in team.members if m.status == MemberStatus.active}
    if user_id not in member_ids:
        raise HTTPException(status_code=403, detail="Only team members can use AI tools")


@router.post("/pitch-deck/{project_id}")
async def generate_pitch_deck(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates a 10-slide investor pitch deck from project context.
    Returns slide JSON + pre-signed .pptx download URL.
    """
    project_data, team_data, milestones = await _get_project_context(project_id, db)

    try:
        result = await ai_service.generate_pitch_deck(project_data, team_data, milestones)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Render to .pptx and upload to S3/R2
    try:
        pptx_bytes = ai_service.render_pptx(
            result["slides"],
            project_title=project_data["title"],
        )
        key = storage_service.upload_bytes(
            pptx_bytes,
            folder=f"pitch-decks/{project_id}",
            filename="pitch_deck.pptx",
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
        download_url = storage_service.get_signed_url(key, expires_in=3600)
    except Exception as e:
        download_url = None  # Degrade gracefully — still return JSON

    return {
        "project_id": str(project_id),
        "slides": result["slides"],
        "download_url": download_url,
    }


@router.post("/lean-canvas/{project_id}")
async def generate_lean_canvas(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates the 9-block Lean Canvas for the project.
    """
    project_data, _, _ = await _get_project_context(project_id, db)

    try:
        canvas = await ai_service.generate_lean_canvas(project_data)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"project_id": str(project_id), "lean_canvas": canvas}


@router.get("/readiness/{project_id}")
async def startup_readiness(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a 0–100 startup readiness score across 5 axes with
    actionable next steps and top risks.
    """
    project_data, team_data, milestones = await _get_project_context(project_id, db)

    completed_count = sum(1 for m in milestones if m["status"] == MilestoneStatus.completed.value)

    try:
        score = await ai_service.startup_readiness_score(project_data, team_data, completed_count)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"project_id": str(project_id), "readiness": score}


@router.get("/skill-gaps/{project_id}")
async def skill_gap_analysis(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compares required skills vs. current team skills.
    Returns gaps, coverage %, and recommended skill domains to recruit.
    """
    proj_result = await db.execute(
        select(Project)
        .options(selectinload(Project.required_skills).selectinload(ProjectRequiredSkill.skill))  # FIX: was .selectinload(Project.required_skills) — infinite self-ref
        .where(Project.project_id == project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    team_result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.members)
            .selectinload(TeamMember.user)
        )
        .where(Team.project_id == project_id)
    )
    team = team_result.scalar_one_or_none()

    from models.skill import UserSkill
    from sqlalchemy.orm import selectinload as sl

    # Collect team skill names
    team_skills = set()
    if team:
        for member in team.members:
            if member.status == MemberStatus.active and member.user:
                user_skills_result = await db.execute(
                    select(UserSkill)
                    .options(selectinload(UserSkill.skill))
                    .where(UserSkill.user_id == member.user_id)
                )
                for us in user_skills_result.scalars().all():
                    if us.skill:
                        team_skills.add(us.skill.skill_name)

    required_skills = [rs.skill.skill_name for rs in project.required_skills if rs.skill]
    covered = [s for s in required_skills if s in team_skills]
    gaps = [s for s in required_skills if s not in team_skills]
    coverage_pct = round(len(covered) / max(len(required_skills), 1) * 100, 1)

    return {
        "project_id": str(project_id),
        "required_skills": required_skills,
        "covered_skills": covered,
        "skill_gaps": gaps,
        "coverage_percent": coverage_pct,
        "recommendation": "Recruit a Designer" if coverage_pct < 60 else "Team skill coverage is healthy",
    }


# ── New Dynamic Feature Endpoints ─────────────────────────────────────────────

from pydantic import BaseModel
from typing import List as TypingList


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: TypingList[ChatMessage] = []


@router.post("/chat/{project_id}")
async def cofounder_chat(
    project_id: UUID,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI Co-Founder Chat — project-scoped multi-turn advisor.
    Knows the full live state: team members, milestones, stage.
    Adapts advice by the caller's domain (engineering / design / business).
    Supports multi-turn via conversation_history parameter.
    """
    project_data, team_data, milestones = await _get_project_context(project_id, db)

    try:
        reply = await ai_service.cofounder_chat(
            project_data=project_data,
            team_data=team_data,
            milestones=milestones,
            caller_domain=current_user.domain.value,
            message=body.message,
            conversation_history=[h.model_dump() for h in body.conversation_history],
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "project_id": str(project_id),
        "reply": reply,
        "caller_domain": current_user.domain.value,
    }


@router.post("/roadmap/{project_id}")
async def generate_roadmap(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Smart Roadmap Generator — 3-sprint (6-week) plan that reads each
    member's availability_hours from their profile and won't overcommit.
    Assigns deliverables to the right domain, surfaces critical path,
    fires bandwidth_warning and missing_role_alert when needed.
    """
    proj_result = await db.execute(
        select(Project).where(Project.project_id == project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from models.user import UserProfile
    team_result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.members)
            .selectinload(TeamMember.user)
            .selectinload(User.profile)
        )
        .where(Team.project_id == project_id)
    )
    team = team_result.scalar_one_or_none()

    milestones_result = await db.execute(
        select(Milestone).where(Milestone.project_id == project_id)
    )
    milestones = milestones_result.scalars().all()

    project_data = {
        "title": project.title,
        "description": project.description,
        "problem_statement": project.problem_statement,
        "target_market": project.target_market,
        "stage": project.stage.value,
    }
    team_data = {
        "members": [
            {
                "name": m.user.full_name,
                "domain": m.user.domain.value,
                "availability_hours": (
                    m.user.profile.availability_hours
                    if m.user.profile and hasattr(m.user.profile, "availability_hours")
                    else 10
                ),
            }
            for m in (team.members if team else [])
            if m.status == MemberStatus.active and m.user
        ]
    }
    milestone_list = [
        {"title": ms.title, "status": ms.status.value}
        for ms in milestones
    ]

    try:
        roadmap = await ai_service.generate_roadmap(project_data, team_data, milestone_list)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"project_id": str(project_id), "roadmap": roadmap}


class IdeaValidateRequest(BaseModel):
    title: str
    problem: str
    market: str
    industry: str = ""
    description: str = ""


@router.post("/validate")
async def validate_idea(
    body: IdeaValidateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Idea Validator — called from Create Project wizard BEFORE the project is saved.
    Returns viability score, overall grade (A–F), green/red flags,
    recommended team composition, MVP suggestion, and pivot suggestions.
    No DB write — pure LLM evaluation.
    """
    try:
        result = await ai_service.validate_idea(
            title=body.title,
            problem=body.problem,
            market=body.market,
            industry=body.industry,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return result
