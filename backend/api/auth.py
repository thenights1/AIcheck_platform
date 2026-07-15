"""Authentication API — login and registration."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_config
from backend.store import get_user_store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _ensure_default_admin() -> None:
    store = get_user_store()
    if store.count_users() > 0:
        return
    cfg = get_config().auth
    uid = uuid.uuid4().hex
    store.create_user(uid, cfg.default_admin_username, cfg.default_admin_password, "admin")


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict
    agent_token: str = ""


@router.post("/login")
def login(req: LoginRequest) -> AuthResponse:
    _ensure_default_admin()
    store = get_user_store()
    user = store.get_user_by_username(req.username)
    if user is None or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    cfg = get_config().auth
    token = jwt.encode(
        {
            "user_id": user["user_id"],
            "username": user["username"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=cfg.token_expire_hours),
        },
        cfg.secret_key,
        algorithm="HS256",
    )
    return AuthResponse(
        token=token,
        user={"user_id": user["user_id"], "username": user["username"], "role": user["role"]},
        agent_token=user.get("agent_token", ""),
    )


@router.post("/register")
def register(req: RegisterRequest) -> AuthResponse:
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")

    store = get_user_store()
    try:
        user = store.create_user(uuid.uuid4().hex, req.username, req.password, "user")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cfg = get_config().auth
    token = jwt.encode(
        {
            "user_id": user["user_id"],
            "username": user["username"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=cfg.token_expire_hours),
        },
        cfg.secret_key,
        algorithm="HS256",
    )
    return AuthResponse(
        token=token,
        user={"user_id": user["user_id"], "username": user["username"], "role": user["role"]},
        agent_token=user.get("agent_token", ""),
    )


def verify_token(token: str) -> dict | None:
    try:
        cfg = get_config().auth
        payload = jwt.decode(token, cfg.secret_key, algorithms=["HS256"])
        return {"user_id": payload["user_id"], "username": payload["username"]}
    except Exception:
        return None
