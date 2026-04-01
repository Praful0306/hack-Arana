import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, Enum, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class ProjectStage(str, enum.Enum):
    ideation = "ideation"
    mvp = "mvp"
    validation = "validation"
    scaling = "scaling"


class ProjectStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class SkillPriority(str, enum.Enum):
    required = "required"
    preferred = "preferred"


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    founder_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    problem_statement = Column(Text, nullable=True)
    target_market = Column(Text, nullable=True)
    industry_vertical = Column(String(100), nullable=True)
    stage = Column(Enum(ProjectStage), default=ProjectStage.ideation, nullable=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.open, nullable=False)
    max_team_size = Column(Integer, default=4)
    momentum_score = Column(Float, default=0.0)        # 0–100, recomputed on milestone events
    view_count = Column(Integer, default=0)
    embedding_version = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    founder = relationship("User", back_populates="created_projects")
    required_skills = relationship("ProjectRequiredSkill", back_populates="project")
    team = relationship("Team", back_populates="project", uselist=False)
    milestones = relationship("Milestone", back_populates="project")


class ProjectRequiredSkill(Base):
    __tablename__ = "project_required_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills_taxonomy.skill_id"), nullable=False)
    priority = Column(Enum(SkillPriority), default=SkillPriority.required)

    project = relationship("Project", back_populates="required_skills")
    skill = relationship("Skill")
