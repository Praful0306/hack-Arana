from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.project import Project
from models.team import Team, TeamMember, TeamInvitation, InvitationStatus, MemberStatus
from schemas.team_milestone import TeamOut, InviteRequest, InviteResponse

router = APIRouter(prefix="/teams", tags=["Teams"])


def _compute_diversity(domains: list[str]) -> float:
    """Shannon diversity index normalised to 0–1 for 3 domains."""
    if not domains:
        return 0.0
    from collections import Counter
    import math
    counts = Counter(domains)
    total = len(domains)
    entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
    max_entropy = math.log(3)  # 3 possible domains
    return round(entropy / max_entropy, 4)


async def _get_team(team_id: UUID, db: AsyncSession) -> Team:
    result = await db.execute(
        select(Team)
        .options(
            selectinload(Team.members).selectinload(TeamMember.user),
            selectinload(Team.invitations),
        )
        .where(Team.team_id == team_id)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Creates a team for a project. Only the project founder can do this."""
    proj_result = await db.execute(select(Project).where(Project.project_id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.founder_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only founder can create team")

    # Check no team already exists
    existing = await db.execute(select(Team).where(Team.project_id == project_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Team already exists for this project")

    team = Team(project_id=project_id, name=f"Team {project.title[:20]}")
    db.add(team)
    await db.flush()

    # Add founder as first member
    db.add(TeamMember(
        team_id=team.team_id,
        user_id=current_user.user_id,
        role_assigned="Founder",
    ))
    await db.commit()
    return await _get_team(team.team_id, db)


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _get_team(team_id, db)


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a team invitation. Only current active team members can invite.
    """
    team = await _get_team(body.team_id, db)

    # Verify inviter is on the team
    is_member = any(m.user_id == current_user.user_id for m in team.members)
    if not is_member:
        raise HTTPException(status_code=403, detail="Only team members can send invitations")

    # Check target user exists
    invitee_result = await db.execute(select(User).where(User.user_id == body.invitee_id))
    invitee = invitee_result.scalar_one_or_none()
    if not invitee:
        raise HTTPException(status_code=404, detail="Invited user not found")

    # Check already a member
    already_member = any(m.user_id == body.invitee_id for m in team.members)
    if already_member:
        raise HTTPException(status_code=409, detail="User is already on the team")

    # Check for pending invite
    pending = await db.execute(
        select(TeamInvitation).where(
            TeamInvitation.team_id == body.team_id,
            TeamInvitation.invitee_id == body.invitee_id,
            TeamInvitation.status == InvitationStatus.pending,
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Pending invitation already exists")

    invite = TeamInvitation(
        team_id=body.team_id,
        inviter_id=current_user.user_id,
        invitee_id=body.invitee_id,
        message=body.message,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return InviteResponse(invitation_id=invite.invitation_id, status=invite.status)


@router.post("/invitations/{invitation_id}/respond")
async def respond_to_invitation(
    invitation_id: UUID,
    accept: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept or decline a team invitation.
    On accept: adds user to team, recalculates diversity score.
    """
    result = await db.execute(
        select(TeamInvitation)
        .options(selectinload(TeamInvitation.team).selectinload(Team.members))
        .where(TeamInvitation.invitation_id == invitation_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invite.invitee_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not your invitation")
    if invite.status != InvitationStatus.pending:
        raise HTTPException(status_code=409, detail="Invitation already resolved")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.status = InvitationStatus.expired
        await db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    if not accept:
        invite.status = InvitationStatus.declined
        await db.commit()
        return {"detail": "Invitation declined"}

    # Check team capacity
    team = invite.team
    active_members = [m for m in team.members if m.status == MemberStatus.active]
    project_result = await db.execute(select(Project).where(Project.project_id == team.project_id))
    project = project_result.scalar_one()
    if len(active_members) >= project.max_team_size:
        raise HTTPException(status_code=409, detail="Team is already full")

    # Add member
    db.add(TeamMember(
        team_id=team.team_id,
        user_id=current_user.user_id,
        role_assigned=None,
    ))
    invite.status = InvitationStatus.accepted

    # Recalculate diversity score
    all_domains = [m.user.domain.value for m in active_members if m.user] + [current_user.domain.value]
    team.diversity_score = _compute_diversity(all_domains)

    await db.commit()

    # Invalidate match cache for this user
    # (redis cache cleared asynchronously — best effort)
    from workers.tasks import rebuild_user_embedding
    rebuild_user_embedding.delay(str(current_user.user_id))

    return {"detail": "Invitation accepted", "team_id": str(team.team_id)}


@router.delete("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_team(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.user_id,
            TeamMember.status == MemberStatus.active,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="You are not an active member of this team")

    member.status = MemberStatus.left
    await db.commit()
