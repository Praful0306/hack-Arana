from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from models.user import UserRole, UserDomain


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    domain: UserDomain

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class OAuthCallbackRequest(BaseModel):
    code: str
    provider: str  # "github" | "google"


# ── Skill ─────────────────────────────────────────────────────────────────────

class SkillOut(BaseModel):
    skill_id: UUID
    skill_name: str
    category: Optional[str]
    domain: str

    class Config:
        from_attributes = True

class AddSkillRequest(BaseModel):
    skill_id: UUID
    proficiency_level: int = Field(..., ge=1, le=5)

class UserSkillOut(BaseModel):
    skill: SkillOut
    proficiency_level: int
    verification_source: str
    verified: bool

    class Config:
        from_attributes = True


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    github_url: Optional[str] = None
    figma_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    institution: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=8)
    location: Optional[str] = None
    availability_hours: Optional[int] = Field(None, ge=1, le=168)
    risk_tolerance: Optional[int] = Field(None, ge=1, le=10)
    interests: Optional[str] = None


# ── User responses ────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    role: UserRole
    domain: UserDomain
    reputation_score: float
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileOut(BaseModel):
    bio: Optional[str]
    avatar_url: Optional[str]
    github_url: Optional[str]
    figma_url: Optional[str]
    linkedin_url: Optional[str]
    institution: Optional[str]
    year_of_study: Optional[int]
    availability_hours: Optional[int]
    interests: Optional[str]

    class Config:
        from_attributes = True

class UserDetailOut(UserOut):
    profile: Optional[UserProfileOut]
    skills: List[UserSkillOut] = []
