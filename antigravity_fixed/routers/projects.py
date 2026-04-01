from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user
from models.user import User
from models.project import Project, ProjectRequiredSkill, ProjectStatus
from models.skill import Skill
from schemas.project import ProjectCreate, ProjectUpdate, ProjectOut, RequiredSkillOut, RequiredSkillIn
from workers.tasks import rebuild_project_embedding

router = APIRouter(prefix="/projects", tags=["Projects"])


async def _load_project(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.required_skills).selectinload(ProjectRequiredSkill.skill)
        )
        .where(Project.project_id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(
        founder_id=current_user.user_id,
        title=body.title,
        description=body.description,
        problem_statement=body.problem_statement,
        target_market=body.target_market,
        industry_vertical=body.industry_vertical,
        stage=body.stage,
        max_team_size=body.max_team_size,
    )
    db.add(project)
    await db.flush()

    for rs in body.required_skills:
        skill_check = await db.execute(select(Skill).where(Skill.skill_id == rs.skill_id))
        if not skill_check.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"Skill {rs.skill_id} not found")
        db.add(ProjectRequiredSkill(
            project_id=project.project_id,
            skill_id=rs.skill_id,
            priority=rs.priority,
        ))

    await db.commit()
    rebuild_project_embedding.delay(str(project.project_id))
    return await _load_project(project.project_id, db)


@router.get("/", response_model=List[ProjectOut])
async def list_projects(
    status: Optional[ProjectStatus] = Query(None),
    stage: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Project).options(
        selectinload(Project.required_skills).selectinload(ProjectRequiredSkill.skill)
    )
    if status:
        q = q.where(Project.status == status)
    if stage:
        q = q.where(Project.stage == stage)

    q = q.order_by(Project.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await _load_project(project_id, db)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _load_project(project_id, db)
    if project.founder_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the project founder can edit this project")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(project, field, val)

    await db.commit()
    rebuild_project_embedding.delay(str(project.project_id))
    return await _load_project(project_id, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _load_project(project_id, db)
    if project.founder_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only the founder can archive this project")
    project.status = ProjectStatus.archived
    await db.commit()


@router.post("/{project_id}/skills", response_model=ProjectOut)
async def add_required_skill(
    project_id: UUID,
    body: RequiredSkillIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _load_project(project_id, db)
    if project.founder_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Only founder can modify required skills")

    skill_check = await db.execute(select(Skill).where(Skill.skill_id == body.skill_id))
    if not skill_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Skill not found")

    db.add(ProjectRequiredSkill(
        project_id=project_id,
        skill_id=body.skill_id,
        priority=body.priority,
    ))
    await db.commit()
    rebuild_project_embedding.delay(str(project_id))
    return await _load_project(project_id, db)
