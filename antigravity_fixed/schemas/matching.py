from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID


class MatchExplanation(BaseModel):
    bm25_score: float
    semantic_score: float
    diversity_score: float
    reputation_score: float
    momentum_score: float = 0.0    # NEW: normalised 0-1 project momentum signal
    final_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    diversity_breakdown: Dict[str, Any]

class RankedProjectMatch(BaseModel):
    project_id: UUID
    title: str
    description: str
    stage: str
    industry_vertical: Optional[str]
    required_skills: List[str]
    current_team_size: int
    max_team_size: int
    momentum_score: float = 0.0    # NEW: raw 0–100 score shown in UI bar
    match: MatchExplanation

class RankedUserMatch(BaseModel):
    user_id: UUID
    full_name: str
    domain: str
    skills: List[str]
    reputation_score: float
    availability_hours: int
    match: MatchExplanation

class ProjectMatchResponse(BaseModel):
    matches: List[RankedProjectMatch]
    total: int
    used_ai: bool               # False when cold-start fallback is used

class UserMatchResponse(BaseModel):
    matches: List[RankedUserMatch]
    total: int
    used_ai: bool
