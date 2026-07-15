"""Scan/Task API — create, list, view, delete compliance tasks."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from backend.api.auth import verify_token
from backend.models import (
    ComplianceTask,
    SkillResult,
    TaskCreateRequest,
    TaskStatus,
    TaskSummary,
)
from backend.registry import get_registry
from backend.store import get_task_store

router = APIRouter(prefix="/api/scan", tags=["scan"])


def _get_user(authorization: str | None = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.removeprefix("Bearer ")
    user = verify_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def _summarize(task: ComplianceTask, results: list[SkillResult]) -> TaskSummary:
    return TaskSummary(
        task_id=task.task_id,
        task_name=task.task_name,
        target_folder=task.target_folder,
        status=task.status,
        progress=task.progress,
        total_skills=task.total_skills,
        completed_skills=task.completed_skills,
        created_at=task.created_at,
        pass_count=sum(1 for r in results if r.status == "pass"),
        fail_count=sum(1 for r in results if r.status == "fail"),
        error_count=sum(1 for r in results if r.status == "error"),
        agent_name=task.agent_name,
    )


@router.post("")
def create_task(req: TaskCreateRequest, authorization: str | None = Header(None)) -> dict:
    user_info = _get_user(authorization) if authorization else {"user_id": "", "username": "anonymous"}
    store = get_task_store()
    registry = get_registry()

    unknown = [s for s in req.skills if s not in registry]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown skills: {unknown}")

    agent_name = ""
    if req.agent_id:
        from backend.api.agent import _registered_agents
        ag = _registered_agents.get(req.agent_id)
        if ag and ag.online:
            agent_name = ag.name
        else:
            raise HTTPException(status_code=400, detail="Selected agent is offline or not found")

    task_id = uuid.uuid4().hex
    task = ComplianceTask(
        task_id=task_id,
        task_name=req.task_name,
        target_folder=req.target_folder,
        skills=req.skills,
        total_skills=len(req.skills),
        user_id=user_info.get("user_id", ""),
        agent_id=req.agent_id or None,
        agent_name=agent_name or None,
    )
    store.save_task(task)

    results = [
        SkillResult(
            skill_name=name,
            skill_label=registry[name].label,
            status="pending",
        )
        for name in req.skills
    ]
    store.save_results(task_id, results)

    # Dispatch task to agent — send skill metadata (no paths, agent resolves locally)
    if req.agent_id:
        import asyncio
        from backend.api.agent import send_agent_command
        skills_meta = []
        for name in req.skills:
            entry = registry.get(name)
            skills_meta.append({
                "name": name,
                "label": entry.label,
                "description": entry.description,
            })
        asyncio.ensure_future(send_agent_command(req.agent_id, {
            "type": "task",
            "task_id": task_id,
            "task_name": req.task_name,
            "target_folder": req.target_folder,
            "skills": req.skills,
            "skills_meta": skills_meta,
        }))

    return {"task_id": task_id, **task.model_dump()}


@router.get("")
def list_tasks(authorization: str | None = Header(None)) -> list[dict]:
    _get_user(authorization) if authorization else None
    store = get_task_store()
    tasks = store.list_tasks()
    summaries = []
    for t in tasks:
        results = store.get_results(t.task_id)
        summaries.append(_summarize(t, results).model_dump())
    return summaries


@router.get("/{task_id}")
def get_task_detail(task_id: str, authorization: str | None = Header(None)) -> dict:
    _get_user(authorization) if authorization else None
    store = get_task_store()
    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    results = store.get_results(task_id)
    return {
        **task.model_dump(),
        "results": [r.model_dump() for r in results],
        "summary": _summarize(task, results).model_dump(),
    }


@router.delete("/{task_id}")
def delete_task(task_id: str, authorization: str | None = Header(None)) -> dict:
    _get_user(authorization) if authorization else None
    store = get_task_store()
    if store.delete_task(task_id):
        return {"ok": True}
    raise HTTPException(status_code=404, detail="Task not found")
