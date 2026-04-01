import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, ForeignKey, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class MemberStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    left = "left"


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    expired = "expired"


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    health_score = Column(Float, default=100.0)        # Decays on inactivity / missed milestones
    diversity_score = Column(Float, default=0.0)       # Domain diversity index 0–1
    equity_split_status = Column(String(50), default="pending")
    formed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="team")
    members = relationship("TeamMember", back_populates="team")
    invitations = relationship("TeamInvitation", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"

    member_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    role_assigned = Column(String(100), nullable=True)  # e.g. "Lead Engineer", "Product Designer"
    joined_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(MemberStatus), default=MemberStatus.active)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class TeamInvitation(Base):
    __tablename__ = "team_invitations"

    invitation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False, index=True)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    invitee_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    message = Column(Text, nullable=True)
    status = Column(Enum(InvitationStatus), default=InvitationStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    team = relationship("Team", back_populates="invitations")
