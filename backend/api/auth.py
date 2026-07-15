"""Authentication API — simplified for demo."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import get_config

router = APIRouter(prefix="/api/auth", tags=["auth"])

_users: dict[str, dict] = {}
_tokens: dict[str, str] = {}


def _ensure_default_user() -> None:
    if _users:
        return
    cfg = get_config().auth
    uid = uuid.uuid4().hex
    _users[uid] = {
        "user_id": uid,
        "username": cfg.default_admin_username,
        "password": cfg.default_admin_password,
        "role": "admin",
    }


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


@router.post("/login")
def login(req: LoginRequest) -> LoginResponse:
    _ensure_default_user()
    for u in _users.values():
        if u["username"] == req.username and u["password"] == req.password:
            cfg = get_config().auth
            token = jwt.encode(
                {
                    "user_id": u["user_id"],
                    "username": u["username"],
                    "exp": datetime.now(timezone.utc) + timedelta(hours=cfg.token_expire_hours),
                },
                cfg.secret_key,
                algorithm="HS256",
            )
            _tokens[token] = u["user_id"]
            return LoginResponse(token=token, user={"user_id": u["user_id"], "username": u["username"], "role": u["role"]})
    raise HTTPException(status_code=401, detail="Invalid credentials")


def verify_token(token: str) -> dict | None:
    try:
        cfg = get_config().auth
        payload = jwt.decode(token, cfg.secret_key, algorithms=["HS256"])
        return {"user_id": payload["user_id"], "username": payload["username"]}
    except Exception:
        return None
