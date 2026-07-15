"""HTTP client for reporting task progress and results to the backend."""

from __future__ import annotations

import json

import httpx


class Reporter:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/")
        self.agent_id = ""
        self.agent_name = ""
        self._client = httpx.AsyncClient(timeout=30.0)

    def set_agent_id(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def set_agent_name(self, name: str) -> None:
        self.agent_name = name

    async def send_progress(self, task_id: str, status: str, progress: float = 0,
                            completed_skills: int = 0, error_message: str | None = None) -> None:
        try:
            resp = await self._client.post(
                f"{self.server_url}/api/agent/task/{task_id}/progress",
                json={
                    "status": status,
                    "progress": progress,
                    "completed_skills": completed_skills,
                    "error_message": error_message,
                },
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"Warning: failed to send progress: {e}")

    async def send_result(self, task_id: str, skill_name: str, skill_label: str,
                          status: str, output: str, result_detail: dict = None,
                          started_at: str = None, finished_at: str = None) -> None:
        try:
            resp = await self._client.post(
                f"{self.server_url}/api/agent/task/{task_id}/result",
                json={
                    "skill_name": skill_name,
                    "skill_label": skill_label,
                    "status": status,
                    "output": output,
                    "result_detail": result_detail or {},
                    "started_at": started_at,
                    "finished_at": finished_at,
                },
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"Warning: failed to send result: {e}")

    async def finish_task(self, task_id: str, status: str, progress: float = 100.0,
                          error_message: str | None = None) -> None:
        try:
            resp = await self._client.post(
                f"{self.server_url}/api/agent/task/{task_id}/finish",
                json={
                    "status": status,
                    "progress": progress,
                    "error_message": error_message,
                },
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"Warning: failed to send finish: {e}")

    async def close(self) -> None:
        await self._client.aclose()
