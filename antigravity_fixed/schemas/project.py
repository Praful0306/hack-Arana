from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models.project import ProjectStage, ProjectStatus, SkillPriority


class RequiredSkillIn(BaseModel):
    skill_id: UUID
    priority: SkillPriority = SkillPriority.required

class RequiredSkillOut(BaseModel):
    skill_id: UUID
    skill_name: str
    priority: SkillPriority

    class Config:
        from_attributes = True

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    problem_statement: Optional[str] = None
    target_market: Optional[str] = None
    industry_vertical: Optional[str] = None
    stage: ProjectStage = ProjectStage.ideation
    max_team_size: int = Field(4, ge=2, le=8)
    required_skills: List[RequiredSkillIn] = []

class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    problem_statement: Optional[str] = None
    target_market: Optional[str] = None
    industry_vertical: Optional[str] = None
    stage: Optional[ProjectStage] = None
    status: Optional[ProjectStatus] = None
    max_team_size: Optional[int] = Field(None, ge=2, le=8)

class ProjectOut(BaseModel):
    project_id: UUID
    founder_id: UUID
    title: str
    description: str
    problem_statement: Optional[str]
    target_market: Optional[str]
    industry_vertical: Optional[str]
    stage: ProjectStage
    status: ProjectStatus
    max_team_size: int
    momentum_score: float = 0.0
    view_count: int = 0
    required_skills: List[RequiredSkillOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
