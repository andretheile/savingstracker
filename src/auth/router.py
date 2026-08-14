"""Google OAuth routes, session, and household membership APIs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.auth.service import (
    AuthDeniedError,
    create_household_invite,
    delete_household_invite,
    list_household_identities,
    list_household_invites,
    normalize_email,
    remove_household_member,
    resolve_google_user,
)
from src.config import settings
from src.core.dependencies import get_db

pages_router = APIRouter(tags=["auth"])
api_router = APIRouter(prefix="/auth", tags=["auth"])
household_router = APIRouter(prefix="/household", tags=["household"])


def _oauth():
    from authlib.integrations.starlette_client import OAuth

    if not settings.google_client_id or not settings.google_client_secret:
        return None
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def _callback_url(request: Request) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/") + "/auth/callback"
    return str(request.url_for("auth_callback"))


def _html_error(title: str, body: str, code: int = 403) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><html><body style='font-family:system-ui;padding:2rem'>"
        f"<h1>{title}</h1><p>{body}</p><p><a href='/login'>Try again</a></p>"
        f"</body></html>",
        status_code=code,
    )


@pages_router.get("/login")
async def login(request: Request):
    oauth = _oauth()
    if oauth is None:
        return _html_error(
            "Google login is not configured",
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET on the server.",
            503,
        )
    return await oauth.google.authorize_redirect(request, _callback_url(request))


@pages_router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    oauth = _oauth()
    if oauth is None:
        return _html_error("Google login is not configured", "Missing OAuth client.", 503)
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return _html_error("Sign-in failed", "Google rejected the login. Try again.", 400)

    info = token.get("userinfo") or {}
    email = info.get("email") or ""
    name = info.get("name") or ""
    picture = info.get("picture")
    google_sub = info.get("sub")
    try:
        user = await resolve_google_user(
            db,
            email=email,
            name=name,
            picture=picture,
            google_sub=google_sub,
        )
    except AuthDeniedError as exc:
        return _html_error("Access denied", exc.message, 403)

    request.session["user"] = {
        "user_id": str(user.id),
        "email": normalize_email(email),
        "name": name or user.name,
        "picture": picture,
    }
    return RedirectResponse(url="/", status_code=302)


@pages_router.get("/logout")
async def logout_browser(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/", status_code=302)


class AuthMeResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str | None = None


@api_router.get("/me", response_model=AuthMeResponse)
async def auth_me(request: Request, user: CurrentUser):
    session_user = request.session.get("user") or {}
    return AuthMeResponse(
        user_id=str(user.id),
        email=session_user.get("email") or "",
        name=session_user.get("name") or user.name,
        picture=session_user.get("picture"),
    )


@api_router.post("/logout")
async def logout_api(request: Request):
    request.session.pop("user", None)
    return {"ok": True}


class MemberResponse(BaseModel):
    email: str
    name: str
    status: str
    picture: str | None = None


class InviteRequest(BaseModel):
    email: str


@household_router.get("/members", response_model=list[MemberResponse])
async def list_members(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    identities = await list_household_identities(db, user.id)
    invites = await list_household_invites(db, user.id)
    members = [
        MemberResponse(email=row.email, name=row.name, status="active", picture=row.picture)
        for row in identities
    ]
    members.extend(
        MemberResponse(email=row.email, name="", status="pending")
        for row in invites
    )
    return members


@household_router.post("/invites", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    data: InviteRequest,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    inviter = (request.session.get("user") or {}).get("email") or ""
    try:
        invite = await create_household_invite(db, user.id, data.email, inviter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return MemberResponse(email=invite.email, name="", status="pending")


@household_router.delete("/invites/{email}")
async def cancel_invite(email: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        await delete_household_invite(db, user.id, email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"ok": True}


@household_router.delete("/members/{email}")
async def remove_member(email: str, user: CurrentUser, db: AsyncSession = Depends(get_db)):
    try:
        await remove_household_member(db, user.id, email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"ok": True}
