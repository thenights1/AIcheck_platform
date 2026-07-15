"""Agent package download endpoint — serves a zip containing agent + skills."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])

AGENT_FILES = [
    "main.py",
    "config.py",
    "server.py",
    "runner.py",
    "reporter.py",
]

@router.get("/download")
def download_agent_package():
    """Download the complete agent package as a zip file.

    Contains: agent/ code, compliance_skills/, agent.yaml, requirements.txt, run_agent.bat
    The user only needs to have opencode CLI installed locally.
    """
    repo_root = Path(__file__).resolve().parents[2]
    agent_dir = repo_root / "agent"
    skills_dir = repo_root / "compliance_skills"
    agent_yaml = repo_root / "agent.yaml"
    requirements = repo_root / "requirements.txt"
    run_bat = repo_root / "run_agent.bat"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # agent/ Python files
        for fname in AGENT_FILES:
            src = agent_dir / fname
            if src.is_file():
                zf.write(src, f"agent/{fname}")

        # agent/ __init__.py
        init = agent_dir / "__init__.py"
        if init.is_file():
            zf.write(init, "agent/__init__.py")

        # compliance_skills/ directory tree
        if skills_dir.is_dir():
            for item in skills_dir.rglob("*"):
                if item.is_file():
                    arcname = str(item.relative_to(repo_root))
                    zf.write(item, arcname)

        # config files
        if agent_yaml.is_file():
            zf.write(agent_yaml, "agent.yaml")
        if requirements.is_file():
            zf.write(requirements, "requirements.txt")
        if run_bat.is_file():
            zf.write(run_bat, "run_agent.bat")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=compliance-audit-agent.zip",
        },
    )
