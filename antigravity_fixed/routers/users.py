from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from database import get_db
from core.dependencies import get_current_user
from models.user import User, UserProfile
from models.skill import Skill, UserSkill
from schemas.user import (
    UserDetailOut, UserOut, ProfileUpdate,
    AddSkillRequest, UserSkillOut, SkillOut
)
from workers.tasks import rebuild_user_embedding

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserDetailOut)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.skills).selectinload(UserSkill.skill),
        )
        .where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserDetailOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile))
        .where(User.user_id == current_user.user_id)
    )
    user = result.scalar_one()

    if not user.profile:
        user.profile = UserProfile(user_id=user.user_id)
        db.add(user.profile)

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(user.profile, field, val)

    await db.commit()
    await db.refresh(user)

    # Rebuild embedding asynchronously
    rebuild_user_embedding.delay(str(user.user_id))

    return user


@router.post("/me/skills", response_model=UserSkillOut, status_code=status.HTTP_201_CREATED)
async def add_skill(
    body: AddSkillRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate skill exists
    skill_result = await db.execute(select(Skill).where(Skill.skill_id == body.skill_id))
    skill = skill_result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found in taxonomy")

    # Check if already added
    existing = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == current_user.user_id,
            UserSkill.skill_id == body.skill_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Skill already added")

    user_skill = UserSkill(
        user_id=current_user.user_id,
        skill_id=body.skill_id,
        proficiency_level=body.proficiency_level,
    )
    db.add(user_skill)
    await db.commit()
    await db.refresh(user_skill)

    # Trigger embedding rebuild
    rebuild_user_embedding.delay(str(current_user.user_id))

    # Load with skill relationship for response
    result = await db.execute(
        select(UserSkill)
        .options(selectinload(UserSkill.skill))
        .where(UserSkill.user_skill_id == user_skill.user_skill_id)
    )
    return result.scalar_one()


@router.delete("/me/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_skill(
    skill_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSkill).where(
            UserSkill.user_id == current_user.user_id,
            UserSkill.skill_id == skill_id,
        )
    )
    user_skill = result.scalar_one_or_none()
    if not user_skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    await db.delete(user_skill)
    await db.commit()
    rebuild_user_embedding.delay(str(current_user.user_id))


@router.get("/skills/taxonomy", response_model=list[SkillOut])
async def list_skills(db: AsyncSession = Depends(get_db)):
    """Returns the full skills taxonomy for use in frontend dropdowns."""
    result = await db.execute(select(Skill).order_by(Skill.domain, Skill.skill_name))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserDetailOut)
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.skills).selectinload(UserSkill.skill),
        )
        .where(User.user_id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
