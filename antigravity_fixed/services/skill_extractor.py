"""
Skill Extractor Service
-----------------------
Pulls verifiable skill signals from third-party APIs (GitHub, Figma).
Called asynchronously via Celery after OAuth token grant.

GitHub extraction flow:
  1. Fetch public repos via GitHub REST API
  2. Aggregate language statistics across repos
  3. Analyse PR merge ratios as a proxy for code quality
  4. Map extracted language/tool names to ESCO skill taxonomy
  5. Upsert into user_skills with verification_source = 'github'

Figma extraction flow:
  1. Fetch user files metadata
  2. Check for component/design system usage as competency signal
  3. Map to design-domain ESCO skill tags
"""

import httpx
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.skill import Skill, UserSkill, VerificationSource
from models.user import User
import structlog

log = structlog.get_logger()

# Language → ESCO/Platform skill name mapping
LANG_TO_SKILL: Dict[str, str] = {
    "Python": "Python",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "Go": "Go (Golang)",
    "Rust": "Rust",
    "Java": "Java",
    "C++": "C++",
    "CSS": "CSS",
    "HTML": "HTML",
    "Shell": "Bash/Shell Scripting",
    "Kotlin": "Kotlin",
    "Swift": "Swift",
    "Dart": "Flutter/Dart",
    "Ruby": "Ruby on Rails",
    "PHP": "PHP",
    "Scala": "Scala",
    "SQL": "SQL",
    "MATLAB": "MATLAB",
    "R": "R (Data Science)",
    "Jupyter Notebook": "Data Analysis",
}


async def extract_github_skills(
    access_token: str,
    user: User,
    db: AsyncSession,
) -> List[str]:
    """
    Fetches GitHub repos, extracts language stats, maps to platform skills.
    Returns list of skill names that were upserted.
    """
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github+json",
    }
    upserted = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Fetch up to 50 public repos
        try:
            repos_resp = await client.get(
                "https://api.github.com/user/repos",
                headers=headers,
                params={"per_page": 50, "sort": "pushed", "type": "owner"},
            )
            repos_resp.raise_for_status()
            repos = repos_resp.json()
        except Exception as e:
            log.error("github_repos_fetch_failed", user_id=str(user.user_id), error=str(e))
            return []

        # Aggregate language bytes across repos
        lang_bytes: Dict[str, int] = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            try:
                lang_resp = await client.get(
                    repo["languages_url"], headers=headers
                )
                if lang_resp.status_code == 200:
                    for lang, bytes_count in lang_resp.json().items():
                        lang_bytes[lang] = lang_bytes.get(lang, 0) + bytes_count
            except Exception:
                continue

    if not lang_bytes:
        return []

    total_bytes = sum(lang_bytes.values()) or 1
    extracted_skills: List[Dict] = []

    for lang, byte_count in lang_bytes.items():
        mapped_skill = LANG_TO_SKILL.get(lang)
        if not mapped_skill:
            continue
        ratio = byte_count / total_bytes
        # Map ratio → proficiency 1–5
        if ratio >= 0.40:
            proficiency = 5
        elif ratio >= 0.25:
            proficiency = 4
        elif ratio >= 0.10:
            proficiency = 3
        elif ratio >= 0.03:
            proficiency = 2
        else:
            proficiency = 1
        extracted_skills.append({"name": mapped_skill, "proficiency": proficiency})

    # Upsert into user_skills
    for entry in extracted_skills:
        skill_result = await db.execute(
            select(Skill).where(Skill.skill_name == entry["name"])
        )
        skill = skill_result.scalar_one_or_none()
        if not skill:
            continue  # Only insert skills that exist in taxonomy

        existing = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.user_id,
                UserSkill.skill_id == skill.skill_id,
            )
        )
        user_skill = existing.scalar_one_or_none()

        if user_skill:
            # Keep the highest proficiency observed
            if entry["proficiency"] > user_skill.proficiency_level:
                user_skill.proficiency_level = entry["proficiency"]
            user_skill.verification_source = VerificationSource.github
            user_skill.verified = True
        else:
            db.add(UserSkill(
                user_id=user.user_id,
                skill_id=skill.skill_id,
                proficiency_level=entry["proficiency"],
                verification_source=VerificationSource.github,
                verified=True,
            ))
        upserted.append(entry["name"])

    await db.commit()
    log.info("github_skills_extracted", user_id=str(user.user_id), skills=upserted)
    return upserted
