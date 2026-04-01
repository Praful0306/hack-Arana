import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, Enum, DateTime, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class MilestoneStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    review = "review"
    completed = "completed"
    blocked = "blocked"


class DeliverableType(str, enum.Enum):
    github_repo = "github_repo"
    figma_link = "figma_link"
    document = "document"
    pitch_deck = "pitch_deck"
    demo_video = "demo_video"
    market_research = "market_research"


# Valid FSM transitions
MILESTONE_TRANSITIONS = {
    MilestoneStatus.pending: [MilestoneStatus.active],
    MilestoneStatus.active: [MilestoneStatus.review, MilestoneStatus.blocked],
    MilestoneStatus.review: [MilestoneStatus.completed, MilestoneStatus.active],
    MilestoneStatus.blocked: [MilestoneStatus.active],
    MilestoneStatus.completed: [],
}


class Milestone(Base):
    __tablename__ = "milestones"

    milestone_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.pending, nullable=False)
    github_pr_link = Column(String(500), nullable=True)
    figma_node_id = Column(String(255), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
    deliverables = relationship("MilestoneDeliverable", back_populates="milestone")

    def can_transition_to(self, new_status: MilestoneStatus) -> bool:
        return new_status in MILESTONE_TRANSITIONS.get(self.status, [])


class MilestoneDeliverable(Base):
    __tablename__ = "milestone_deliverables"

    deliverable_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.milestone_id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    deliverable_type = Column(Enum(DeliverableType), nullable=False)
    file_url = Column(String(1000), nullable=False)
    file_name = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone", back_populates="deliverables")
