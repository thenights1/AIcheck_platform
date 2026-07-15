"""Agent WebSocket endpoint — agent connects here to receive commands."""

from __future__ import annotations

import asyncio
import json
import socket
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from backend.logger import get_logger
from backend.models import AgentInfo, AgentRemoteConfig, SkillResult, TaskStatus
from backend.store import get_task_store

logger = get_logger(__name__)

router = APIRouter(tags=["agent"])
public_router = APIRouter(tags=["agent_public"])

_registered_agents: dict[str, AgentInfo] = {}
_agent_ws: dict[str, WebSocket] = {}
_agent_configs: dict[str, AgentRemoteConfig] = {}


def _send_json(ws: WebSocket, data: dict):
    return asyncio.create_task(ws.send_text(json.dumps(data, ensure_ascii=False)))


@router.websocket("/api/agent/ws")
async def agent_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    agent_id = None
    try:
        msg = await websocket.receive_json()
        if msg.get("type") != "hello":
            await websocket.close(code=4000)
            return

        name = msg.get("name") or socket.gethostname()
        agent_id = uuid.uuid4().hex
        ip = websocket.client.host if websocket.client else "unknown"

        agent_info = AgentInfo(
            agent_id=agent_id,
            name=name,
            ip=ip,
            last_seen=datetime.now(timezone.utc).isoformat(),
        )
        _registered_agents[agent_id] = agent_info
        _agent_ws[agent_id] = websocket

        reported_config = msg.get("config")
        if reported_config and name not in _agent_configs:
            try:
                _agent_configs[name] = AgentRemoteConfig(**reported_config)
            except Exception:
                pass

        cfg = _agent_configs.get(name, AgentRemoteConfig())
        await _send_json(websocket, {
            "type": "welcome",
            "agent_id": agent_id,
            "config": cfg.model_dump(),
        })

        logger.info("Agent connected: %s (%s)", agent_id, name)

        while True:
            incoming = await websocket.receive_json()
            _touch_agent(agent_id)
            if isinstance(incoming, dict) and incoming.get("type") == "heartbeat":
                await _send_json(websocket, {"type": "heartbeat_ack"})
                continue

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("Agent WS error for %s: %s", agent_id, e)
    finally:
        if agent_id:
            _agent_ws.pop(agent_id, None)
            ag = _registered_agents.pop(agent_id, None)
            if ag:
                logger.info("Agent disconnected: %s (%s)", agent_id, ag.name)


def _touch_agent(agent_id: str) -> None:
    ag = _registered_agents.get(agent_id)
    if ag:
        ag.last_seen = datetime.now(timezone.utc).isoformat()
        ag.online = True


async def send_agent_command(agent_id: str, command: dict) -> bool:
    ws = _agent_ws.get(agent_id)
    if ws is None:
        return False
    try:
        await ws.send_text(json.dumps(command, ensure_ascii=False))
        return True
    except Exception:
        return False


@public_router.get("/api/agent/list")
def list_agents() -> list[dict]:
    return [
        {
            "agent_id": a.agent_id,
            "name": a.name,
            "ip": a.ip,
            "last_seen": a.last_seen,
            "online": a.online,
        }
        for a in _registered_agents.values()
    ]


# ----- Agent → Server result receivers (HTTP POST) -----


@public_router.post("/api/agent/task/{task_id}/progress")
async def agent_task_progress(request: Request, task_id: str):
    """Receive progress update from agent."""
    body = await request.json()
    store = get_task_store()
    status = body.get("status", "running")
    try:
        st = TaskStatus(status)
    except ValueError:
        st = TaskStatus.RUNNING
    store.set_task_status(
        task_id,
        status=st,
        progress=body.get("progress"),
        completed_skills=body.get("completed_skills"),
        error_message=body.get("error_message"),
    )
    return {"ok": True}


@public_router.post("/api/agent/task/{task_id}/result")
async def agent_task_result(request: Request, task_id: str):
    """Receive a single skill result from agent."""
    body = await request.json()
    store = get_task_store()
    results = store.get_results(task_id)
    skill_name = body.get("skill_name", "")

    for r in results:
        if r.skill_name == skill_name:
            r.status = body.get("status", "pending")
            r.output = body.get("output", "")
            r.result_detail = body.get("result_detail", {})
            r.started_at = body.get("started_at")
            r.finished_at = body.get("finished_at")
            break
    else:
        results.append(SkillResult(
            skill_name=skill_name,
            skill_label=body.get("skill_label", skill_name),
            status=body.get("status", "pending"),
            output=body.get("output", ""),
            result_detail=body.get("result_detail", {}),
            started_at=body.get("started_at"),
            finished_at=body.get("finished_at"),
        ))

    store.save_results(task_id, results)

    completed = sum(1 for r in results if r.status in ("pass", "fail", "error"))
    total = len(results)
    store.set_task_status(
        task_id,
        status=TaskStatus.RUNNING,
        progress=round(completed / total * 100, 1) if total else 0,
        completed_skills=completed,
    )
    return {"ok": True}


@public_router.post("/api/agent/task/{task_id}/finish")
async def agent_task_finish(request: Request, task_id: str):
    """Receive task finish notification from agent."""
    body = await request.json()
    store = get_task_store()
    status = body.get("status", "complete")
    try:
        st = TaskStatus(status)
    except ValueError:
        st = TaskStatus.COMPLETE
    store.set_task_status(
        task_id,
        status=st,
        progress=body.get("progress", 100.0),
        error_message=body.get("error_message"),
    )
    logger.info("Task %s finished with status: %s", task_id, status)
    return {"ok": True}
