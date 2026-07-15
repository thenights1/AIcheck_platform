"""Agent package download — injects user's agent_token into agent.yaml."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from backend.store import get_user_store

router = APIRouter(prefix="/api/agent", tags=["agent"])

AGENT_FILES = [
    "main.py",
    "config.py",
    "server.py",
    "runner.py",
    "reporter.py",
]

_OWNER_TOKEN_RE = re.compile(r'^(\s*owner_token:\s*).*$', re.MULTILINE)


def _parse_auth(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    from backend.api.auth import verify_token
    return verify_token(token)


@router.get("/download")
def download_agent_package(authorization: str | None = Header(None)):
    """Download agent package with user's agent_token injected."""
    user = _parse_auth(authorization)
    agent_token = ""
    if user:
        store = get_user_store()
        u = store.get_user(user["user_id"])
        if u:
            agent_token = u.get("agent_token", "")

    repo_root = Path(__file__).resolve().parents[2]
    agent_dir = repo_root / "agent"
    skills_dir = repo_root / "compliance_skills"
    agent_yaml = repo_root / "agent.yaml"
    requirements = repo_root / "requirements.txt"
    run_bat = repo_root / "run_agent.bat"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in AGENT_FILES:
            src = agent_dir / fname
            if src.is_file():
                zf.write(src, f"agent/{fname}")

        init = agent_dir / "__init__.py"
        if init.is_file():
            zf.write(init, "agent/__init__.py")

        if skills_dir.is_dir():
            for item in skills_dir.rglob("*"):
                if item.is_file():
                    arcname = str(item.relative_to(repo_root))
                    zf.write(item, arcname)

        if requirements.is_file():
            zf.write(requirements, "requirements.txt")

        if run_bat.is_file():
            zf.write(run_bat, "run_agent.bat")

        # Inject agent_token into agent.yaml
        if agent_yaml.is_file():
            yaml_content = agent_yaml.read_text(encoding="utf-8")
            if _OWNER_TOKEN_RE.search(yaml_content):
                yaml_content = _OWNER_TOKEN_RE.sub(
                    f'\\g<1>"{agent_token}"', yaml_content
                )
            else:
                yaml_content = yaml_content.rstrip() + f'\nowner_token: "{agent_token}"\n'
            zf.writestr("agent.yaml", yaml_content)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=compliance-audit-agent.zip",
        },
    )
