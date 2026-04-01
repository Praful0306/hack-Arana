from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import httpx

from database import get_db
from models.user import User, UserProfile
from schemas.user import RegisterRequest, LoginRequest, TokenResponse, OAuthCallbackRequest
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from config import settings
from workers.tasks import rebuild_user_embedding

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        full_name=body.full_name,
        domain=body.domain,
        auth_hash=hash_password(body.password),
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # Get user_id before committing

    profile = UserProfile(user_id=user.user_id)
    db.add(profile)
    await db.commit()

    access = create_access_token(str(user.user_id), {"domain": user.domain.value, "role": user.role.value})
    refresh = create_refresh_token(str(user.user_id))

    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.auth_hash or not verify_password(body.password, user.auth_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    access = create_access_token(str(user.user_id), {"domain": user.domain.value, "role": user.role.value})
    refresh = create_refresh_token(str(user.user_id))
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate tokens
    new_access = create_access_token(str(user.user_id), {"domain": user.domain.value, "role": user.role.value})
    new_refresh = create_refresh_token(str(user.user_id))
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=new_access)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"detail": "Logged out"}


@router.post("/oauth/github", response_model=TokenResponse)
async def oauth_github(body: OAuthCallbackRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Exchange GitHub OAuth code for user profile, upsert user, issue JWT.
    Triggers async GitHub skill extraction via Celery.
    """
    async with httpx.AsyncClient() as client:
        # Step 1: Exchange code for access_token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": body.code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(status_code=400, detail="GitHub token exchange failed")

        # Step 2: Fetch GitHub user profile
        profile_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github+json"},
        )
        gh_user = profile_resp.json()
        email = gh_user.get("email") or f"{gh_user['login']}@github.local"

    # Step 3: Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        from models.user import UserDomain
        user = User(
            email=email,
            full_name=gh_user.get("name") or gh_user.get("login", "GitHub User"),
            domain=UserDomain.engineering,  # Default; user can change in profile
            is_verified=True,
        )
        db.add(user)
        await db.flush()
        profile = UserProfile(
            user_id=user.user_id,
            github_url=f"https://github.com/{gh_user.get('login')}",
            github_access_token=gh_token,
        )
        db.add(profile)
    else:
        if user.profile:
            user.profile.github_access_token = gh_token

    await db.commit()

    # Step 4: Trigger async skill extraction
    if gh_token:
        from workers.tasks import extract_github_skills_task
        extract_github_skills_task.delay(str(user.user_id), gh_token)

    access = create_access_token(str(user.user_id), {"domain": user.domain.value, "role": user.role.value})
    refresh = create_refresh_token(str(user.user_id))
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
