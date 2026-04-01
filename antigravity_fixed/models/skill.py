import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import enum


class VerificationSource(str, enum.Enum):
    self_reported = "self_reported"
    github = "github"
    figma = "figma"
    linkedin = "linkedin"
    peer = "peer"


class SkillDomain(str, enum.Enum):
    engineering = "engineering"
    design = "design"
    business = "business"
    cross = "cross"


class Skill(Base):
    __tablename__ = "skills_taxonomy"

    skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100))                     # e.g. "Frontend", "Branding", "GTM"
    domain = Column(Enum(SkillDomain), nullable=False)
    parent_skill_id = Column(UUID(as_uuid=True), ForeignKey("skills_taxonomy.skill_id"), nullable=True)
    esco_code = Column(String(50), nullable=True)      # ESCO/O*NET standard code

    user_skills = relationship("UserSkill", back_populates="skill")


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_skill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False, index=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills_taxonomy.skill_id"), nullable=False)
    proficiency_level = Column(Integer, nullable=False, default=1)  # 1–5
    verification_source = Column(Enum(VerificationSource), default=VerificationSource.self_reported)
    verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill", back_populates="user_skills")
