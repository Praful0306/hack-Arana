from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import bcrypt
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get("JWT_SECRET", "antigravity-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

app = FastAPI(title="Antigravity API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class UserDomain(str):
    engineering = "engineering"
    design = "design"
    business = "business"

class ProjectStage(str):
    ideation = "ideation"
    mvp = "mvp"
    validation = "validation"
    scaling = "scaling"

class MilestoneStatus(str):
    pending = "pending"
    active = "active"
    review = "review"
    completed = "completed"
    blocked = "blocked"

# Auth Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    domain: str  # engineering, design, business

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    bio: Optional[str] = None
    institution: Optional[str] = None
    year_of_study: Optional[int] = None
    availability_hours: Optional[int] = None
    risk_tolerance: Optional[int] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None

class SkillCreate(BaseModel):
    skill_id: str
    proficiency: int  # 1-5

# Project Models
class ProjectCreate(BaseModel):
    title: str
    description: str
    problem_statement: Optional[str] = None
    target_market: Optional[str] = None
    industry_vertical: Optional[str] = None
    stage: str = "ideation"
    max_team_size: int = 4

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    problem_statement: Optional[str] = None
    target_market: Optional[str] = None
    industry_vertical: Optional[str] = None
    stage: Optional[str] = None
    max_team_size: Optional[int] = None

class RequiredSkillCreate(BaseModel):
    skill_id: str
    priority: str = "required"  # required, preferred

# Milestone Models
class MilestoneCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    owner_domain: Optional[str] = None

class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None

# AI Models
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []

class IdeaValidateRequest(BaseModel):
    title: str
    problem: str
    market: str
    industry: str = ""
    description: str = ""

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        del user["_id"]
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict"""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.post("/auth/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if body.domain not in ["engineering", "design", "business"]:
        raise HTTPException(status_code=400, detail="Invalid domain")
    
    user_doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "full_name": body.full_name,
        "domain": body.domain,
        "role": "student",
        "is_active": True,
        "is_verified": False,
        "reputation_score": 0.0,
        "onboarding_complete": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "profile": {
            "bio": None,
            "institution": None,
            "year_of_study": None,
            "availability_hours": 10,
            "risk_tolerance": 5,
            "github_url": None,
            "linkedin_url": None,
            "portfolio_url": None
        },
        "skills": []
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "full_name": body.full_name,
        "domain": body.domain,
        "role": "student",
        "onboarding_complete": False,
        "access_token": access_token
    }

@api_router.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "full_name": user["full_name"],
        "domain": user["domain"],
        "role": user.get("role", "student"),
        "onboarding_complete": user.get("onboarding_complete", False),
        "access_token": access_token
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        access_token = create_access_token(str(user["_id"]), user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600, path="/")
        
        return {"access_token": access_token}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ═══════════════════════════════════════════════════════════════════════════════
# USER ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.patch("/users/me")
async def update_profile(body: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {"updated_at": datetime.now(timezone.utc)}
    for field, value in body.model_dump(exclude_unset=True).items():
        update_data[f"profile.{field}"] = value
    
    await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$set": update_data})
    return {"message": "Profile updated"}

@api_router.post("/users/me/skills")
async def add_skills(skills: List[SkillCreate], current_user: dict = Depends(get_current_user)):
    skill_docs = []
    for skill in skills:
        skill_info = await db.skills_taxonomy.find_one({"_id": ObjectId(skill.skill_id)})
        if skill_info:
            skill_docs.append({
                "skill_id": skill.skill_id,
                "skill_name": skill_info["name"],
                "domain": skill_info["domain"],
                "proficiency": skill.proficiency
            })
    
    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"skills": skill_docs, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Skills updated", "skills": skill_docs}

@api_router.post("/users/me/complete-onboarding")
async def complete_onboarding(current_user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"onboarding_complete": True, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Onboarding completed"}

@api_router.get("/users/skills/taxonomy")
async def get_skills_taxonomy():
    skills = await db.skills_taxonomy.find({}, {"_id": 0}).to_list(1000)
    if not skills:
        # Seed default skills
        default_skills = [
            # Engineering
            {"id": str(uuid.uuid4()), "name": "Python", "domain": "engineering", "category": "Backend"},
            {"id": str(uuid.uuid4()), "name": "JavaScript", "domain": "engineering", "category": "Frontend"},
            {"id": str(uuid.uuid4()), "name": "React", "domain": "engineering", "category": "Frontend"},
            {"id": str(uuid.uuid4()), "name": "Node.js", "domain": "engineering", "category": "Backend"},
            {"id": str(uuid.uuid4()), "name": "Machine Learning", "domain": "engineering", "category": "AI/ML"},
            {"id": str(uuid.uuid4()), "name": "AWS", "domain": "engineering", "category": "DevOps"},
            {"id": str(uuid.uuid4()), "name": "PostgreSQL", "domain": "engineering", "category": "Database"},
            {"id": str(uuid.uuid4()), "name": "MongoDB", "domain": "engineering", "category": "Database"},
            # Design
            {"id": str(uuid.uuid4()), "name": "UI Design", "domain": "design", "category": "Visual"},
            {"id": str(uuid.uuid4()), "name": "UX Research", "domain": "design", "category": "Research"},
            {"id": str(uuid.uuid4()), "name": "Figma", "domain": "design", "category": "Tools"},
            {"id": str(uuid.uuid4()), "name": "Prototyping", "domain": "design", "category": "Process"},
            {"id": str(uuid.uuid4()), "name": "User Testing", "domain": "design", "category": "Research"},
            {"id": str(uuid.uuid4()), "name": "Brand Design", "domain": "design", "category": "Visual"},
            # Business
            {"id": str(uuid.uuid4()), "name": "Market Research", "domain": "business", "category": "Strategy"},
            {"id": str(uuid.uuid4()), "name": "Financial Modeling", "domain": "business", "category": "Finance"},
            {"id": str(uuid.uuid4()), "name": "Go-to-Market", "domain": "business", "category": "Strategy"},
            {"id": str(uuid.uuid4()), "name": "Sales", "domain": "business", "category": "Revenue"},
            {"id": str(uuid.uuid4()), "name": "Marketing", "domain": "business", "category": "Growth"},
            {"id": str(uuid.uuid4()), "name": "Fundraising", "domain": "business", "category": "Finance"},
        ]
        for skill in default_skills:
            skill["_id"] = ObjectId()
            skill["id"] = str(skill["_id"])
        await db.skills_taxonomy.insert_many(default_skills)
        skills = default_skills
    
    # Group by domain
    grouped = {"engineering": [], "design": [], "business": []}
    for skill in skills:
        domain = skill.get("domain", "engineering")
        if domain in grouped:
            grouped[domain].append({"id": skill.get("id", str(skill.get("_id", ""))), "name": skill["name"], "category": skill.get("category", "")})
    
    return grouped

@api_router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_doc(user)

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.post("/projects")
async def create_project(body: ProjectCreate, current_user: dict = Depends(get_current_user)):
    project_doc = {
        "founder_id": current_user["id"],
        "founder_name": current_user["full_name"],
        "founder_domain": current_user["domain"],
        "title": body.title,
        "description": body.description,
        "problem_statement": body.problem_statement,
        "target_market": body.target_market,
        "industry_vertical": body.industry_vertical,
        "stage": body.stage,
        "status": "open",
        "max_team_size": body.max_team_size,
        "momentum_score": 0.0,
        "view_count": 0,
        "required_skills": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    result = await db.projects.insert_one(project_doc)
    project_id = str(result.inserted_id)
    
    # Auto-create team
    team_doc = {
        "project_id": project_id,
        "name": f"{body.title} Team",
        "health_score": 50.0,
        "diversity_score": 33.0,
        "members": [{
            "user_id": current_user["id"],
            "name": current_user["full_name"],
            "domain": current_user["domain"],
            "role": "founder",
            "status": "active",
            "joined_at": datetime.now(timezone.utc).isoformat()
        }],
        "created_at": datetime.now(timezone.utc)
    }
    await db.teams.insert_one(team_doc)
    
    return {"id": project_id, **body.model_dump()}

@api_router.get("/projects")
async def list_projects(founder_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if founder_id == "me":
        query["founder_id"] = current_user["id"]
    elif founder_id:
        query["founder_id"] = founder_id
    
    projects = await db.projects.find(query).sort("created_at", -1).to_list(100)
    return [serialize_doc(p) for p in projects]

@api_router.get("/projects/{project_id}")
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Increment view count
    await db.projects.update_one({"_id": ObjectId(project_id)}, {"$inc": {"view_count": 1}})
    
    return serialize_doc(project)

@api_router.patch("/projects/{project_id}")
async def update_project(project_id: str, body: ProjectUpdate, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["founder_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = body.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
    return {"message": "Project updated"}

@api_router.post("/projects/{project_id}/required-skills")
async def add_required_skill(project_id: str, body: RequiredSkillCreate, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["founder_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    skill_info = await db.skills_taxonomy.find_one({"id": body.skill_id})
    if not skill_info:
        skill_info = await db.skills_taxonomy.find_one({"_id": ObjectId(body.skill_id)})
    
    skill_name = skill_info["name"] if skill_info else "Unknown"
    
    skill_doc = {
        "id": str(uuid.uuid4()),
        "skill_id": body.skill_id,
        "skill_name": skill_name,
        "priority": body.priority
    }
    
    await db.projects.update_one(
        {"_id": ObjectId(project_id)},
        {"$push": {"required_skills": skill_doc}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )
    return skill_doc

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.get("/teams/{project_id}")
async def get_team(project_id: str, current_user: dict = Depends(get_current_user)):
    team = await db.teams.find_one({"project_id": project_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return serialize_doc(team)

@api_router.post("/teams/invite")
async def invite_to_team(project_id: str, user_id: str, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["founder_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    invitee = await db.users.find_one({"_id": ObjectId(user_id)})
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")
    
    invitation = {
        "_id": ObjectId(),
        "project_id": project_id,
        "project_title": project["title"],
        "inviter_id": current_user["id"],
        "inviter_name": current_user["full_name"],
        "invitee_id": user_id,
        "invitee_name": invitee["full_name"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.invitations.insert_one(invitation)
    return {"message": "Invitation sent", "id": str(invitation["_id"])}

@api_router.get("/invitations")
async def get_invitations(current_user: dict = Depends(get_current_user)):
    invitations = await db.invitations.find({"invitee_id": current_user["id"], "status": "pending"}).to_list(100)
    return [serialize_doc(i) for i in invitations]

@api_router.post("/invitations/{invitation_id}/respond")
async def respond_to_invitation(invitation_id: str, accept: bool, current_user: dict = Depends(get_current_user)):
    invitation = await db.invitations.find_one({"_id": ObjectId(invitation_id)})
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation["invitee_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    status = "accepted" if accept else "declined"
    await db.invitations.update_one({"_id": ObjectId(invitation_id)}, {"$set": {"status": status}})
    
    if accept:
        await db.teams.update_one(
            {"project_id": invitation["project_id"]},
            {"$push": {"members": {
                "user_id": current_user["id"],
                "name": current_user["full_name"],
                "domain": current_user["domain"],
                "role": "member",
                "status": "active",
                "joined_at": datetime.now(timezone.utc).isoformat()
            }}}
        )
        # Recalculate diversity
        team = await db.teams.find_one({"project_id": invitation["project_id"]})
        if team:
            domains = set(m["domain"] for m in team.get("members", []))
            diversity = (len(domains) / 3) * 100
            await db.teams.update_one({"project_id": invitation["project_id"]}, {"$set": {"diversity_score": diversity}})
    
    return {"message": f"Invitation {status}"}

# ═══════════════════════════════════════════════════════════════════════════════
# MILESTONE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.post("/projects/{project_id}/milestones")
async def create_milestone(project_id: str, body: MilestoneCreate, current_user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    milestone_doc = {
        "_id": ObjectId(),
        "project_id": project_id,
        "title": body.title,
        "description": body.description,
        "status": "pending",
        "due_date": body.due_date,
        "owner_domain": body.owner_domain,
        "created_by": current_user["id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.milestones.insert_one(milestone_doc)
    return serialize_doc(milestone_doc)

@api_router.get("/projects/{project_id}/milestones")
async def get_milestones(project_id: str, current_user: dict = Depends(get_current_user)):
    milestones = await db.milestones.find({"project_id": project_id}).to_list(100)
    return [serialize_doc(m) for m in milestones]

@api_router.patch("/projects/{project_id}/milestones/{milestone_id}")
async def update_milestone(project_id: str, milestone_id: str, body: MilestoneUpdate, current_user: dict = Depends(get_current_user)):
    milestone = await db.milestones.find_one({"_id": ObjectId(milestone_id), "project_id": project_id})
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    old_status = milestone.get("status")
    update_data = body.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.milestones.update_one({"_id": ObjectId(milestone_id)}, {"$set": update_data})
    
    # Update momentum if status changed to completed
    if body.status == "completed" and old_status != "completed":
        await update_project_momentum(project_id)
    
    return {"message": "Milestone updated"}

async def update_project_momentum(project_id: str):
    """Recalculate project momentum score based on milestone completion"""
    milestones = await db.milestones.find({"project_id": project_id}).to_list(100)
    if not milestones:
        return
    
    completed = sum(1 for m in milestones if m.get("status") == "completed")
    total = len(milestones)
    
    # Base score from completion rate
    base_score = (completed / total) * 60 if total > 0 else 0
    
    # Recency bonus - milestones completed in last 7 days
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_completions = sum(1 for m in milestones 
                            if m.get("status") == "completed" 
                            and m.get("updated_at", datetime.min.replace(tzinfo=timezone.utc)) > recent_cutoff)
    recency_bonus = min(recent_completions * 10, 40)
    
    momentum = min(base_score + recency_bonus, 100)
    
    await db.projects.update_one({"_id": ObjectId(project_id)}, {"$set": {"momentum_score": momentum}})

# ═══════════════════════════════════════════════════════════════════════════════
# MATCHING ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.get("/match/projects")
async def match_projects(current_user: dict = Depends(get_current_user)):
    """Get AI-matched projects for the current user"""
    user_skills = current_user.get("skills", [])
    user_domain = current_user.get("domain", "engineering")
    
    # Get open projects
    projects = await db.projects.find({"status": "open"}).to_list(50)
    
    matches = []
    for project in projects:
        # Skip own projects
        if project["founder_id"] == current_user["id"]:
            continue
        
        # Calculate match score
        required_skills = project.get("required_skills", [])
        user_skill_names = [s["skill_name"].lower() for s in user_skills]
        
        skill_match = 0
        for rs in required_skills:
            if rs["skill_name"].lower() in user_skill_names:
                skill_match += 1
        
        skill_score = (skill_match / len(required_skills) * 40) if required_skills else 20
        
        # Domain diversity bonus
        team = await db.teams.find_one({"project_id": str(project["_id"])})
        team_domains = [m["domain"] for m in team.get("members", [])] if team else []
        diversity_bonus = 30 if user_domain not in team_domains else 10
        
        # Momentum bonus
        momentum_bonus = project.get("momentum_score", 0) * 0.3
        
        final_score = min(skill_score + diversity_bonus + momentum_bonus, 100)
        
        team_size = len(team.get("members", [])) if team else 1
        
        matches.append({
            "project": serialize_doc(project),
            "match_score": round(final_score, 1),
            "skill_match_count": skill_match,
            "team_size": team_size,
            "max_team_size": project.get("max_team_size", 4),
            "used_ai": len(user_skills) >= 3,
            "explanation": {
                "skill_score": round(skill_score, 1),
                "diversity_bonus": round(diversity_bonus, 1),
                "momentum_bonus": round(momentum_bonus, 1)
            }
        })
    
    # Sort by score
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches[:20]

@api_router.get("/match/users")
async def match_users(project_id: str, current_user: dict = Depends(get_current_user)):
    """Get users who might be a good fit for this project"""
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    required_skills = [s["skill_name"].lower() for s in project.get("required_skills", [])]
    
    # Get team domains
    team = await db.teams.find_one({"project_id": project_id})
    team_domains = [m["domain"] for m in team.get("members", [])] if team else []
    team_user_ids = [m["user_id"] for m in team.get("members", [])] if team else []
    
    # Find potential matches
    users = await db.users.find({"is_active": True}).to_list(100)
    
    matches = []
    for user in users:
        if str(user["_id"]) in team_user_ids:
            continue
        
        user_skill_names = [s["skill_name"].lower() for s in user.get("skills", [])]
        
        skill_match = sum(1 for s in required_skills if s in user_skill_names)
        skill_score = (skill_match / len(required_skills) * 50) if required_skills else 25
        
        diversity_bonus = 30 if user["domain"] not in team_domains else 10
        reputation_bonus = min(user.get("reputation_score", 0) * 0.2, 20)
        
        final_score = min(skill_score + diversity_bonus + reputation_bonus, 100)
        
        matches.append({
            "user": {
                "id": str(user["_id"]),
                "full_name": user["full_name"],
                "domain": user["domain"],
                "skills": user.get("skills", [])[:5],
                "reputation_score": user.get("reputation_score", 0)
            },
            "match_score": round(final_score, 1),
            "skill_match_count": skill_match
        })
    
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches[:10]

# ═══════════════════════════════════════════════════════════════════════════════
# AI ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

async def get_openai_chat():
    """Get OpenAI chat instance using Emergent integration"""
    from emergentintegrations.llm.chat import LlmChat
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message="You are a helpful AI assistant for Antigravity, a student startup incubator platform."
    )
    chat.with_model("openai", "gpt-4o")
    return chat

@api_router.post("/ai/validate")
async def validate_idea(body: IdeaValidateRequest, current_user: dict = Depends(get_current_user)):
    """Validate a startup idea before creating a project"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    prompt = f"""You are a startup accelerator judge evaluating a student team's idea.
Be honest and specific. Reference the actual idea details.

Idea:
Title: {body.title}
Problem: {body.problem}
Market: {body.market}
Industry: {body.industry}
Description: {body.description}

Return ONLY valid JSON:
{{
  "viability_score": <0-100>,
  "overall_grade": "A|B|C|D|F",
  "originality_score": <0-100>,
  "cross_disciplinary_need_score": <0-100>,
  "recommended_team_composition": {{
    "engineering_pct": <0-100>,
    "design_pct": <0-100>,
    "business_pct": <0-100>
  }},
  "mvp_suggestion": "Concrete 1-sentence MVP description",
  "green_flags": ["flag1", "flag2", "flag3"],
  "red_flags": ["flag1", "flag2"],
  "pivot_suggestions": ["suggestion1", "suggestion2"],
  "first_customer_hypothesis": "Who is the very first user and why they'd pay",
  "verdict": "2-sentence honest overall verdict"
}}"""

    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message="You are a startup evaluator. Respond with valid JSON only."
    )
    chat.with_model("openai", "gpt-4o")
    
    try:
        response = await chat.send_message(UserMessage(text=prompt))
        import json
        # Clean response
        clean = response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        return json.loads(clean.strip())
    except Exception as e:
        logger.error(f"AI validation error: {e}")
        # Return fallback response
        return {
            "viability_score": 65,
            "overall_grade": "B",
            "originality_score": 60,
            "cross_disciplinary_need_score": 75,
            "recommended_team_composition": {"engineering_pct": 40, "design_pct": 30, "business_pct": 30},
            "mvp_suggestion": "Build a simple landing page with core value proposition",
            "green_flags": ["Clear problem statement", "Identified target market"],
            "red_flags": ["Needs more validation"],
            "pivot_suggestions": ["Consider narrowing target audience"],
            "first_customer_hypothesis": "Early adopters in your network",
            "verdict": "Promising idea with room for refinement. Focus on customer validation."
        }

@api_router.post("/ai/chat/{project_id}")
async def cofounder_chat(project_id: str, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """AI Co-Founder Chat - project-scoped advisor"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    team = await db.teams.find_one({"project_id": project_id})
    milestones = await db.milestones.find({"project_id": project_id}).to_list(50)
    
    project_context = f"{project['title']} | Stage: {project['stage']} | Problem: {project.get('problem_statement', 'Not defined')}"
    team_context = ", ".join(f"{m['name']} ({m['domain']})" for m in team.get("members", [])) if team else "No team members yet"
    milestone_context = [f"{m['title']} [{m['status']}]" for m in milestones] if milestones else ["No milestones set"]
    
    system_message = f"""You are an AI co-founder advisor embedded inside the Antigravity platform.
You have full context of this project's state, team, and milestones.
Adapt your advice based on the caller's domain:
- engineering → architecture, tech stack, API design
- design → UX flows, user research, visual direction
- business → GTM, revenue model, market sizing

Project context: {project_context}
Team: {team_context}
Active milestones: {milestone_context}
Caller domain: {current_user['domain']}

Be direct, specific, and actionable. Reference actual project data in every answer."""

    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"chat-{project_id}-{current_user['id']}",
        system_message=system_message
    )
    chat.with_model("openai", "gpt-4o")
    
    try:
        # Build conversation context
        full_prompt = ""
        for h in body.conversation_history[-10:]:
            role = "User" if h["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {h['content']}\n\n"
        full_prompt += f"User: {body.message}"
        
        response = await chat.send_message(UserMessage(text=full_prompt))
        
        return {
            "project_id": project_id,
            "reply": response,
            "caller_domain": current_user["domain"]
        }
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")

@api_router.post("/ai/roadmap/{project_id}")
async def generate_roadmap(project_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a 3-sprint (6-week) roadmap"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    team = await db.teams.find_one({"project_id": project_id})
    milestones = await db.milestones.find({"project_id": project_id}).to_list(50)
    
    # Get team with availability hours
    team_with_hours = []
    if team:
        for member in team.get("members", []):
            user = await db.users.find_one({"_id": ObjectId(member["user_id"])})
            if user:
                hours = user.get("profile", {}).get("availability_hours", 10)
                team_with_hours.append(f"{member['name']} ({member['domain']}, {hours}h/week)")
    
    context = f"{project['title']} | Problem: {project.get('problem_statement', 'N/A')} | Market: {project.get('target_market', 'N/A')}"
    milestone_titles = [m["title"] for m in milestones]
    
    prompt = f"""You are a senior product manager. Generate a 3-sprint (6-week) roadmap for this student startup.

Rules:
- Read each team member's availability_hours and NEVER assign them more hours than they have per week
- Assign deliverables to the right domain owner
- Surface the critical path — which milestone MUST finish before another can start
- If a required domain is missing from the team, fire a missing_role_alert
- Each sprint is 2 weeks

Project: {context}
Team members with availability: {team_with_hours or ["No team members yet"]}
Existing milestones: {milestone_titles or ["No milestones set"]}
Stage: {project['stage']}

Return ONLY valid JSON:
{{
  "sprints": [
    {{
      "sprint_number": 1,
      "title": "Sprint title",
      "week_range": "Weeks 1-2",
      "goal": "Sprint goal in one sentence",
      "milestones": [
        {{
          "title": "Deliverable title",
          "owner_domain": "engineering|design|business",
          "estimated_hours": 8,
          "is_critical_path": true,
          "depends_on": []
        }}
      ]
    }}
  ],
  "critical_path_summary": "Which items are blocking",
  "bandwidth_warning": null,
  "missing_role_alert": null,
  "definition_of_done": "What success looks like at week 6"
}}"""

    api_key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    
    chat = LlmChat(
        api_key=api_key,
        session_id=str(uuid.uuid4()),
        system_message="You are a startup PM. Respond with valid JSON only."
    )
    chat.with_model("openai", "gpt-4o")
    
    try:
        response = await chat.send_message(UserMessage(text=prompt))
        import json
        clean = response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        
        roadmap = json.loads(clean.strip())
        return {"project_id": project_id, "roadmap": roadmap}
    except Exception as e:
        logger.error(f"Roadmap generation error: {e}")
        raise HTTPException(status_code=502, detail="AI service temporarily unavailable")

@api_router.get("/ai/skill-gaps/{project_id}")
async def skill_gap_analysis(project_id: str, current_user: dict = Depends(get_current_user)):
    """Analyze skill coverage for a project"""
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    team = await db.teams.find_one({"project_id": project_id})
    required_skills = project.get("required_skills", [])
    
    # Collect team skills
    team_skills = set()
    if team:
        for member in team.get("members", []):
            user = await db.users.find_one({"_id": ObjectId(member["user_id"])})
            if user:
                for skill in user.get("skills", []):
                    team_skills.add(skill["skill_name"].lower())
    
    # Analyze gaps
    skills_analysis = []
    covered_count = 0
    for rs in required_skills:
        is_covered = rs["skill_name"].lower() in team_skills
        if is_covered:
            covered_count += 1
        skills_analysis.append({
            "skill_name": rs["skill_name"],
            "priority": rs["priority"],
            "is_covered": is_covered
        })
    
    coverage_pct = (covered_count / len(required_skills) * 100) if required_skills else 100
    
    return {
        "project_id": project_id,
        "coverage_percentage": round(coverage_pct, 1),
        "skills": skills_analysis,
        "gaps": [s for s in skills_analysis if not s["is_covered"]]
    }

@api_router.get("/ai/readiness/{project_id}")
async def startup_readiness(project_id: str, current_user: dict = Depends(get_current_user)):
    """Calculate startup readiness score across multiple dimensions"""
    project = await db.projects.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    team = await db.teams.find_one({"project_id": project_id})
    milestones = await db.milestones.find({"project_id": project_id}).to_list(100)
    
    # Problem Clarity (0-100)
    problem_clarity = 0
    if project.get("problem_statement"):
        problem_clarity += 50
        if len(project["problem_statement"]) > 100:
            problem_clarity += 30
        if project.get("target_market"):
            problem_clarity += 20
    
    # Market Size (0-100) - based on market description completeness
    market_size = 0
    if project.get("target_market"):
        market_size += 50
        if len(project["target_market"]) > 50:
            market_size += 30
        if project.get("industry_vertical"):
            market_size += 20
    
    # Solution Viability (0-100) - based on description and stage
    solution_viability = 20
    if project.get("description"):
        solution_viability += 30
    stage_scores = {"ideation": 10, "mvp": 30, "validation": 50, "scaling": 70}
    solution_viability += stage_scores.get(project["stage"], 10)
    
    # Team Completeness (0-100)
    team_completeness = 33
    if team:
        member_count = len(team.get("members", []))
        domains = set(m["domain"] for m in team.get("members", []))
        team_completeness = min(member_count * 25, 50) + len(domains) * 16
    
    # Execution Evidence (0-100) - based on milestones
    execution_evidence = 0
    if milestones:
        completed = sum(1 for m in milestones if m.get("status") == "completed")
        total = len(milestones)
        execution_evidence = (completed / total * 100) if total > 0 else 0
    
    overall = (problem_clarity + market_size + solution_viability + team_completeness + execution_evidence) / 5
    
    # Generate next actions
    next_actions = []
    if problem_clarity < 70:
        next_actions.append("Refine your problem statement with specific pain points")
    if market_size < 70:
        next_actions.append("Define your total addressable market (TAM)")
    if team_completeness < 70:
        next_actions.append("Recruit team members to fill skill gaps")
    if execution_evidence < 50:
        next_actions.append("Complete your first milestone to build momentum")
    
    # Top risks
    top_risks = []
    if team_completeness < 50:
        top_risks.append("Insufficient team capacity")
    if market_size < 50:
        top_risks.append("Unclear market opportunity")
    if execution_evidence < 30:
        top_risks.append("No validated progress yet")
    
    return {
        "project_id": project_id,
        "overall_score": round(overall, 1),
        "dimensions": {
            "problem_clarity": round(problem_clarity, 1),
            "market_size": round(market_size, 1),
            "solution_viability": round(solution_viability, 1),
            "team_completeness": round(team_completeness, 1),
            "execution_evidence": round(execution_evidence, 1)
        },
        "next_actions": next_actions[:3],
        "top_risks": top_risks[:3]
    }

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH & ROOT
# ═══════════════════════════════════════════════════════════════════════════════

@api_router.get("/")
async def root():
    return {"message": "Antigravity API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup
@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.projects.create_index("founder_id")
    await db.teams.create_index("project_id")
    await db.milestones.create_index("project_id")
    await db.invitations.create_index("invitee_id")
    logger.info("Antigravity API started")

@app.on_event("shutdown")
async def shutdown():
    client.close()
