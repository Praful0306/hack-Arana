import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, ForeignKey,
    Enum, DateTime, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserRole(str, enum.Enum):
    student = "student"
    mentor = "mentor"
    admin = "admin"
    institution_admin = "institution_admin"


class UserDomain(str, enum.Enum):
    engineering = "engineering"
    design = "design"
    business = "business"


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    domain = Column(Enum(UserDomain), nullable=False)
    auth_hash = Column(String(255), nullable=True)     # null for OAuth-only users
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    reputation_score = Column(Float, default=0.0)      # Earned from completed milestones
    embedding_version = Column(Integer, default=0)     # Bump on each re-embed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    skills = relationship("UserSkill", back_populates="user")
    team_memberships = relationship("TeamMember", back_populates="user")
    created_projects = relationship("Project", back_populates="founder")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    github_url = Column(String(255), nullable=True)
    figma_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    portfolio_url = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    location = Column(String(100), nullable=True)
    availability_hours = Column(Integer, default=10)   # hrs/week available
    risk_tolerance = Column(Integer, default=5)        # 1–10 scale
    interests = Column(Text, nullable=True)            # comma-separated tags

    # OAuth tokens (encrypted at rest)
    github_access_token = Column(Text, nullable=True)
    figma_access_token = Column(Text, nullable=True)

    user = relationship("User", back_populates="profile")
