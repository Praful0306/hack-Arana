"""
Celery Workers
--------------
All CPU-heavy / I/O-bound tasks run here, decoupled from the API thread.

Tasks:
  rebuild_user_embedding   — Regenerate user vector after skill/profile update
  rebuild_project_embedding — Regenerate project vector after edit
  extract_github_skills    — Pull skills from GitHub after OAuth grant
  recalculate_health_scores — Daily job: decay team health scores
  send_milestone_reminders — Daily job: email teams with overdue milestones
"""

import asyncio
from celery import Celery
from celery.schedules import crontab
from config import settings
import structlog

log = structlog.get_logger()

celery_app = Celery(
    "antigravity",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "recalculate-health-scores-daily": {
            "task": "workers.tasks.recalculate_health_scores",
            "schedule": crontab(hour=0, minute=0),
        },
        "send-milestone-reminders-daily": {
            "task": "workers.tasks.send_milestone_reminders",
            "schedule": crontab(hour=8, minute=0),
        },
        "recalculate-momentum-scores-hourly": {
            "task": "workers.tasks.recalculate_momentum_scores",
            "schedule": crontab(minute=0),  # every hour
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="workers.tasks.rebuild_user_embedding", bind=True, max_retries=3)
def rebuild_user_embedding(self, user_id: str):
    """
    Triggered after: skill add/remove, profile update, GitHub OAuth link.
    Rebuilds the user's embedding vector and stores it in Redis.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from models.user import User
        from models.skill import UserSkill
        from services.embedding_service import build_user_text, embed_text, store_embedding
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User)
                .options(
                    selectinload(User.profile),
                    selectinload(User.skills).selectinload(UserSkill.skill),  # FIX: nested load
                )
                .where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                log.warning("rebuild_user_embedding_user_not_found", user_id=user_id)
                return

            text = build_user_text(user, user.profile, user.skills)
            vec = await embed_text(text)
            key = f"embedding:user:{user_id}"
            await store_embedding(redis, key, vec)

            # Bump embedding version for cache invalidation
            user.embedding_version += 1
            await db.commit()
            log.info("user_embedding_rebuilt", user_id=user_id)
        await redis.aclose()

    try:
        _run_async(_run())
    except Exception as exc:
        log.error("rebuild_user_embedding_failed", user_id=user_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="workers.tasks.rebuild_project_embedding", bind=True, max_retries=3)
def rebuild_project_embedding(self, project_id: str):
    """Triggered after project create/update."""
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from models.project import Project
        from services.embedding_service import build_project_text, embed_text, store_embedding
        import redis.asyncio as aioredis

        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Project)
                .options(selectinload(Project.required_skills))
                .where(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                return

            text = build_project_text(project, project.required_skills)
            vec = await embed_text(text)
            key = f"embedding:project:{project_id}"
            await store_embedding(redis, key, vec)

            project.embedding_version += 1
            await db.commit()
            log.info("project_embedding_rebuilt", project_id=project_id)
        await redis.aclose()

    try:
        _run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="workers.tasks.extract_github_skills")
def extract_github_skills_task(user_id: str, access_token: str):
    """
    Triggered after a user successfully completes GitHub OAuth.
    Extracts language stats, upserts skills, then triggers embedding rebuild.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select
        from models.user import User
        from services.skill_extractor import extract_github_skills

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            skills = await extract_github_skills(access_token, user, db)
            log.info("github_extraction_complete", user_id=user_id, count=len(skills))

    _run_async(_run())
    # Chain: after extraction, rebuild embedding
    rebuild_user_embedding.delay(user_id)


@celery_app.task(name="workers.tasks.recalculate_health_scores")
def recalculate_health_scores():
    """
    Daily: decays team health scores based on overdue milestones + inactivity.
    Teams with health < 40 → mentor_alert flag set.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select, func
        from models.team import Team
        from models.milestone import Milestone, MilestoneStatus
        from datetime import datetime, date

        async with AsyncSessionLocal() as db:
            teams_result = await db.execute(select(Team))
            teams = teams_result.scalars().all()

            today = date.today()
            for team in teams:
                # Count overdue milestones
                overdue_result = await db.execute(
                    select(func.count(Milestone.milestone_id)).where(
                        Milestone.project_id == team.project_id,
                        Milestone.due_date < today,
                        Milestone.status.not_in([MilestoneStatus.completed]),
                    )
                )
                overdue = overdue_result.scalar() or 0

                # Simple decay: -10 per overdue milestone, floor at 0
                team.health_score = max(0.0, team.health_score - (overdue * 10))

                if team.health_score < 40:
                    log.warning("low_team_health", team_id=str(team.team_id), score=team.health_score)
                    # TODO: trigger mentor notification via notification service

            await db.commit()
            log.info("health_scores_recalculated", teams_processed=len(teams))

    _run_async(_run())


@celery_app.task(name="workers.tasks.send_milestone_reminders")
def send_milestone_reminders():
    """
    Daily at 8am UTC: emails teams whose milestones are due within 3 days.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select
        from models.milestone import Milestone, MilestoneStatus
        from models.team import Team, TeamMember
        from models.user import User
        from datetime import date, timedelta

        reminder_window = date.today() + timedelta(days=3)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Milestone).where(
                    Milestone.due_date <= reminder_window,
                    Milestone.due_date >= date.today(),
                    Milestone.status.in_([MilestoneStatus.pending, MilestoneStatus.active]),
                )
            )
            milestones = result.scalars().all()
            log.info("milestone_reminders_queued", count=len(milestones))
            # TODO: for each milestone, fetch team members' emails and call email service

    _run_async(_run())


@celery_app.task(name="workers.tasks.recalculate_momentum_scores")
def recalculate_momentum_scores():
    """
    Hourly: recomputes momentum_score (0–100) for every open project.
    Formula: 30% milestone velocity + 30% recent activity + 20% team completeness + 20% view traction.
    Triggered automatically each hour and also called directly after milestone status changes.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select, func
        from models.project import Project, ProjectStatus
        from models.milestone import Milestone, MilestoneStatus
        from models.team import Team, TeamMember
        from datetime import datetime, timedelta

        async with AsyncSessionLocal() as db:
            projects_result = await db.execute(
                select(Project).where(Project.status == ProjectStatus.open)
            )
            projects = projects_result.scalars().all()

            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            for project in projects:
                # 1. Milestone velocity (0-30): completed milestones in last 30 days
                velocity_result = await db.execute(
                    select(func.count(Milestone.milestone_id)).where(
                        Milestone.project_id == project.project_id,
                        Milestone.status == MilestoneStatus.completed,
                        Milestone.updated_at >= thirty_days_ago,
                    )
                )
                recent_completed = velocity_result.scalar() or 0
                velocity_score = min(recent_completed * 10, 30)

                # 2. Total milestone completion ratio (0-30)
                total_result = await db.execute(
                    select(func.count(Milestone.milestone_id)).where(
                        Milestone.project_id == project.project_id
                    )
                )
                completed_result = await db.execute(
                    select(func.count(Milestone.milestone_id)).where(
                        Milestone.project_id == project.project_id,
                        Milestone.status == MilestoneStatus.completed,
                    )
                )
                total_ms = total_result.scalar() or 1
                completed_ms = completed_result.scalar() or 0
                completion_score = round((completed_ms / total_ms) * 30, 1)

                # 3. Team completeness (0-20): filled slots vs max
                team_result = await db.execute(
                    select(Team).where(Team.project_id == project.project_id)
                )
                team = team_result.scalar_one_or_none()
                if team:
                    member_count_result = await db.execute(
                        select(func.count(TeamMember.member_id)).where(
                            TeamMember.team_id == team.team_id
                        )
                    )
                    member_count = member_count_result.scalar() or 0
                    team_score = round((member_count / max(project.max_team_size, 1)) * 20, 1)
                else:
                    team_score = 0.0

                # 4. View traction (0-20)
                view_score = min(getattr(project, 'view_count', 0) / 5, 20)

                project.momentum_score = round(
                    velocity_score + completion_score + team_score + view_score, 1
                )

            await db.commit()
            log.info("momentum_scores_recalculated", count=len(projects))

    _run_async(_run())


@celery_app.task(name="workers.tasks.trigger_momentum_update")
def trigger_momentum_update(project_id: str):
    """
    Called immediately when a milestone status changes or deliverable is uploaded.
    Recalculates momentum for a single project without waiting for the hourly job.
    """
    async def _run():
        from database import AsyncSessionLocal
        from sqlalchemy import select, func
        from models.project import Project
        from models.milestone import Milestone, MilestoneStatus
        from models.team import Team, TeamMember
        from datetime import datetime, timedelta

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Project).where(Project.project_id == project_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                return

            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            velocity_result = await db.execute(
                select(func.count(Milestone.milestone_id)).where(
                    Milestone.project_id == project.project_id,
                    Milestone.status == MilestoneStatus.completed,
                    Milestone.updated_at >= thirty_days_ago,
                )
            )
            recent_completed = velocity_result.scalar() or 0
            velocity_score = min(recent_completed * 10, 30)

            total_result = await db.execute(
                select(func.count(Milestone.milestone_id)).where(
                    Milestone.project_id == project.project_id
                )
            )
            completed_result = await db.execute(
                select(func.count(Milestone.milestone_id)).where(
                    Milestone.project_id == project.project_id,
                    Milestone.status == MilestoneStatus.completed,
                )
            )
            total_ms = total_result.scalar() or 1
            completed_ms = completed_result.scalar() or 0
            completion_score = round((completed_ms / total_ms) * 30, 1)

            team_result = await db.execute(
                select(Team).where(Team.project_id == project.project_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                mc_result = await db.execute(
                    select(func.count(TeamMember.member_id)).where(
                        TeamMember.team_id == team.team_id
                    )
                )
                member_count = mc_result.scalar() or 0
                team_score = round((member_count / max(project.max_team_size, 1)) * 20, 1)
            else:
                team_score = 0.0

            view_score = min(getattr(project, 'view_count', 0) / 5, 20)
            project.momentum_score = round(velocity_score + completion_score + team_score + view_score, 1)

            await db.commit()
            log.info("momentum_updated_for_project", project_id=project_id, score=project.momentum_score)

    _run_async(_run())
