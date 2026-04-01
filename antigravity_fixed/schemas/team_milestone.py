from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from models.team import InvitationStatus, MemberStatus
from models.milestone import MilestoneStatus, DeliverableType


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamMemberOut(BaseModel):
    member_id: UUID
    user_id: UUID
    full_name: str
    domain: str
    role_assigned: Optional[str]
    joined_at: datetime
    status: MemberStatus

    class Config:
        from_attributes = True

class TeamOut(BaseModel):
    team_id: UUID
    project_id: UUID
    name: Optional[str]
    health_score: float
    diversity_score: float
    equity_split_status: str
    formed_at: datetime
    members: List[TeamMemberOut] = []

    class Config:
        from_attributes = True

class InviteRequest(BaseModel):
    team_id: UUID
    invitee_id: UUID
    message: Optional[str] = None

class InviteResponse(BaseModel):
    invitation_id: UUID
    status: InvitationStatus


# ── Milestone ─────────────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    due_date: Optional[date] = None
    github_pr_link: Optional[str] = None
    figma_node_id: Optional[str] = None

class MilestoneStatusUpdate(BaseModel):
    status: MilestoneStatus

class MilestoneOut(BaseModel):
    milestone_id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    due_date: Optional[date]
    status: MilestoneStatus
    github_pr_link: Optional[str]
    figma_node_id: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class DeliverableCreate(BaseModel):
    deliverable_type: DeliverableType
    file_url: str
    file_name: Optional[str] = None

class DeliverableOut(BaseModel):
    deliverable_id: UUID
    deliverable_type: DeliverableType
    file_url: str
    file_name: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True
