from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.project import Project
from models.team import Team, TeamMember, MemberStatus
from models.milestone import Milestone, MilestoneDeliverable, MilestoneStatus
from schemas.team_milestone import (
    MilestoneCreate, MilestoneStatusUpdate, MilestoneOut,
    DeliverableCreate, DeliverableOut
)

from workers.tasks import trigger_momentum_update

router = APIRouter(prefix="/projects/{project_id}/milestones", tags=["Milestones"])


async def _assert_team_member(project_id: UUID, user: User, db: AsyncSession) -> Team:
    """Raises 403 if the user is not an active member of the project's team."""
    result = await db.execute(
        select(Team)
        .options(selectinload(Team.members))
        .where(Team.project_id == project_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found for this project")

    is_member = any(
        m.user_id == user.user_id and m.status == MemberStatus.active
        for m in team.members
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not an active member of this team")
    return team


@router.get("/", response_model=list[MilestoneOut])
async def list_milestones(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_team_member(project_id, current_user, db)
    result = await db.execute(
        select(Milestone)
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.created_at)
    )
    return result.scalars().all()


@router.post("/", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    project_id: UUID,
    body: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_team_member(project_id, current_user, db)

    milestone = Milestone(
        project_id=project_id,
        created_by=current_user.user_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        github_pr_link=body.github_pr_link,
        figma_node_id=body.figma_node_id,
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


@router.patch("/{milestone_id}/status", response_model=MilestoneOut)
async def update_milestone_status(
    project_id: UUID,
    milestone_id: UUID,
    body: MilestoneStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    FSM-gated status transition.
    Valid transitions: pending→active, active→review|blocked,
                       review→completed|active, blocked→active
    """
    await _assert_team_member(project_id, current_user, db)

    result = await db.execute(
        select(Milestone).where(
            Milestone.milestone_id == milestone_id,
            Milestone.project_id == project_id,
        )
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    if not milestone.can_transition_to(body.status):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot transition from '{milestone.status}' to '{body.status}'",
        )

    milestone.status = body.status
    if body.status == MilestoneStatus.completed:
        milestone.completed_at = datetime.utcnow()
        # Award reputation points to team members
        await _award_reputation(project_id, db)

    await db.commit()
    await db.refresh(milestone)

    # Fire real-time momentum recalculation for this project
    trigger_momentum_update.delay(str(project_id))

    return milestone


@router.post("/{milestone_id}/deliverables", response_model=DeliverableOut, status_code=201)
async def add_deliverable(
    project_id: UUID,
    milestone_id: UUID,
    body: DeliverableCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_team_member(project_id, current_user, db)

    milestone_check = await db.execute(
        select(Milestone).where(
            Milestone.milestone_id == milestone_id,
            Milestone.project_id == project_id,
        )
    )
    if not milestone_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Milestone not found")

    deliverable = MilestoneDeliverable(
        milestone_id=milestone_id,
        uploaded_by=current_user.user_id,
        deliverable_type=body.deliverable_type,
        file_url=body.file_url,
        file_name=body.file_name,
    )
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


@router.get("/{milestone_id}/deliverables", response_model=list[DeliverableOut])
async def list_deliverables(
    project_id: UUID,
    milestone_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _assert_team_member(project_id, current_user, db)
    result = await db.execute(
        select(MilestoneDeliverable).where(
            MilestoneDeliverable.milestone_id == milestone_id
        ).order_by(MilestoneDeliverable.uploaded_at)
    )
    return result.scalars().all()


# ── Webhooks (GitHub PR → milestone auto-advance) ─────────────────────────────

webhook_router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@webhook_router.post("/github")
async def github_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Listens for GitHub 'pull_request' events.
    If PR body contains 'Resolves MS-<uuid>', auto-advances milestone to 'review'.
    """
    if payload.get("action") != "closed" or not payload.get("pull_request", {}).get("merged"):
        return {"detail": "ignored"}

    pr_body: str = payload.get("pull_request", {}).get("body", "")
    pr_url: str = payload.get("pull_request", {}).get("html_url", "")

    import re
    match = re.search(r"Resolves MS-([0-9a-f-]{36})", pr_body, re.IGNORECASE)
    if not match:
        return {"detail": "no milestone reference found"}

    milestone_id = match.group(1)
    result = await db.execute(select(Milestone).where(Milestone.milestone_id == milestone_id))
    milestone = result.scalar_one_or_none()
    if not milestone:
        return {"detail": "milestone not found"}

    if milestone.can_transition_to(MilestoneStatus.review):
        milestone.status = MilestoneStatus.review
        milestone.github_pr_link = pr_url
        await db.commit()

    return {"detail": "milestone advanced to review"}


async def _award_reputation(project_id: UUID, db: AsyncSession):
    """Awards +10 reputation to all active team members on milestone completion."""
    team_result = await db.execute(
        select(Team)
        .options(selectinload(Team.members).selectinload(TeamMember.user))
        .where(Team.project_id == project_id)
    )
    team = team_result.scalar_one_or_none()
    if not team:
        return
    for member in team.members:
        if member.status == MemberStatus.active and member.user:
            member.user.reputation_score += 10
