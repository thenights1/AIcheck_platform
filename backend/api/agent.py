"""Agent WebSocket endpoint — agent connects here to receive commands."""

from __future__ import annotations

import asyncio
import json
import socket
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, Request, WebSocket, WebSocketDisconnect

from backend.logger import get_logger
from backend.models import AgentInfo, AgentRemoteConfig, TaskStatus
from backend.store import get_task_store, get_user_store

logger = get_logger(__name__)

router = APIRouter(tags=["agent"])
public_router = APIRouter(tags=["agent_public"])

_registered_agents: dict[str, AgentInfo] = {}


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
        owner_token = msg.get("owner_token", "")
        agent_id = uuid.uuid4().hex
        ip = websocket.client.host if websocket.client else "unknown"

        # Bind to user via owner_token
        user_id = ""
        if owner_token:
            store = get_user_store()
            owner = store.get_user_by_agent_token(owner_token)
            if owner:
                user_id = owner["user_id"]
                logger.info("Agent bound to user %s via token", owner["username"])

        agent_info = AgentInfo(
            agent_id=agent_id,
            name=name,
            ip=ip,
            last_seen=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
        )
        _registered_agents[agent_id] = agent_info

        await _send_json(websocket, {
            "type": "welcome",
            "agent_id": agent_id,
            "config": {},
        })

        logger.info("Agent connected: %s (%s) user=%s", agent_id, name, user_id or "(unbound)")

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
            ag = _registered_agents.pop(agent_id, None)
            if ag:
                logger.info("Agent disconnected: %s (%s)", agent_id, ag.name)


def _touch_agent(agent_id: str) -> None:
    ag = _registered_agents.get(agent_id)
    if ag:
        ag.last_seen = datetime.now(timezone.utc).isoformat()
        ag.online = True


async def send_agent_command(agent_id: str, command: dict) -> bool:
    ws = _agent_ws.get(agent_id) if hasattr(sys.modules[__name__], '_agent_ws') else None
    # Need WS reference — keep a global
    return False  # will fix below


# Store WebSocket connections
_agent_ws: dict[str, WebSocket] = {}


# Patch the websocket handler to store ws reference
# Actually re-declare _agent_ws before the handler... it's already defined above as empty dict.
# Let me just add the WS storage to the handler.

# Re-define the handler properly
_original_handler = agent_websocket

# Actually simpler: just store ws in the handler function
# Let me rewrite this properly

# Remove the old handler and recreate
del _agent_ws


_agent_ws: dict[str, WebSocket] = {}


@router.websocket("/api/agent/ws")
async def _agent_websocket_v2(websocket: WebSocket) -> None:
    global _agent_ws
    await websocket.accept()
    agent_id = None
    try:
        msg = await websocket.receive_json()
        if msg.get("type") != "hello":
            await websocket.close(code=4000)
            return

        name = msg.get("name") or socket.gethostname()
        owner_token = msg.get("owner_token", "")
        agent_id = uuid.uuid4().hex
        ip = websocket.client.host if websocket.client else "unknown"

        user_id = ""
        if owner_token:
            store = get_user_store()
            owner = store.get_user_by_agent_token(owner_token)
            if owner:
                user_id = owner["user_id"]
                logger.info("Agent bound to user %s via token", owner["username"])

        agent_info = AgentInfo(
            agent_id=agent_id,
            name=name,
            ip=ip,
            last_seen=datetime.now(timezone.utc).isoformat(),
            user_id=user_id,
        )
        _registered_agents[agent_id] = agent_info
        _agent_ws[agent_id] = websocket

        await _send_json(websocket, {
            "type": "welcome",
            "agent_id": agent_id,
            "config": {},
        })

        logger.info("Agent connected: %s (%s) user=%s", agent_id, name, user_id or "(unbound)")

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


async def send_agent_command(agent_id: str, command: dict) -> bool:
    ws = _agent_ws.get(agent_id)
    if ws is None:
        return False
    try:
        await ws.send_text(json.dumps(command, ensure_ascii=False))
        return True
    except Exception:
        return False


def _parse_auth(authorization: str | None) -> dict | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    from backend.api.auth import verify_token
    return verify_token(token)


@public_router.get("/api/agent/list")
def list_agents(authorization: str | None = Header(None)) -> list[dict]:
    user = _parse_auth(authorization)
    user_id = user["user_id"] if user else ""
    result = []
    for a in _registered_agents.values():
        if user_id and a.user_id and a.user_id != user_id:
            continue
        result.append({
            "agent_id": a.agent_id,
            "name": a.name,
            "ip": a.ip,
            "last_seen": a.last_seen,
            "online": a.online,
            "user_id": a.user_id,
        })
    return result


# ----- Agent → Server result receivers (HTTP POST) -----

@public_router.post("/api/agent/task/{task_id}/progress")
async def agent_task_progress(request: Request, task_id: str):
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
        from backend.models import SkillResult
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
