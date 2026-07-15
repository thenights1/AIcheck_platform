"""Simple in-memory + JSON file store for compliance tasks and users."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from backend.models import ComplianceTask, SkillResult, TaskStatus


class UserStore:
    def __init__(self, data_dir: str = "data") -> None:
        self._path = Path(data_dir) / "users.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._users: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._users = data
            except Exception:
                pass

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._users, indent=2), encoding="utf-8")

    def create_user(self, user_id: str, username: str, password: str, role: str = "user") -> dict:
        with self._lock:
            for u in self._users.values():
                if u["username"] == username:
                    raise ValueError("Username already exists")
            import uuid
            agent_token = uuid.uuid4().hex
            user = {
                "user_id": user_id,
                "username": username,
                "password": password,
                "role": role,
                "agent_token": agent_token,
            }
            self._users[user_id] = user
            self._save()
            return dict(user)

    def get_user(self, user_id: str) -> dict | None:
        with self._lock:
            return dict(self._users.get(user_id, {})) or None

    def get_user_by_username(self, username: str) -> dict | None:
        with self._lock:
            for u in self._users.values():
                if u["username"] == username:
                    return dict(u)
            return None

    def get_user_by_agent_token(self, token: str) -> dict | None:
        with self._lock:
            for u in self._users.values():
                if u.get("agent_token") == token:
                    return dict(u)
            return None

    def count_users(self) -> int:
        with self._lock:
            return len(self._users)


class TaskStore:
    """Thread-safe task store backed by JSON files."""

    def __init__(self, data_dir: str = "data/tasks") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._cache: dict[str, ComplianceTask] = {}
        self._results: dict[str, list[SkillResult]] = {}
        self._load_all()

    def _task_path(self, task_id: str) -> Path:
        return self._data_dir / f"{task_id}.json"

    def _results_path(self, task_id: str) -> Path:
        return self._data_dir / f"{task_id}_results.json"

    def _load_all(self) -> None:
        for p in self._data_dir.glob("*.json"):
            if p.name.endswith("_results.json"):
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                task = ComplianceTask(**data)
                self._cache[task.task_id] = task
            except Exception:
                pass
        for p in self._data_dir.glob("*_results.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                task_id = p.name.replace("_results.json", "")
                self._results[task_id] = [SkillResult(**r) for r in data]
            except Exception:
                pass

    def save_task(self, task: ComplianceTask) -> None:
        with self._lock:
            self._cache[task.task_id] = task
            self._task_path(task.task_id).write_text(
                task.model_dump_json(indent=2), encoding="utf-8"
            )

    def get_task(self, task_id: str) -> ComplianceTask | None:
        with self._lock:
            return self._cache.get(task_id)

    def list_tasks(self, user_id: str = "") -> list[ComplianceTask]:
        with self._lock:
            tasks = sorted(
                self._cache.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )
            if user_id:
                tasks = [t for t in tasks if t.user_id == user_id]
            return tasks

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id not in self._cache:
                return False
            del self._cache[task_id]
            self._results.pop(task_id, None)
            tp = self._task_path(task_id)
            rp = self._results_path(task_id)
            if tp.exists():
                tp.unlink()
            if rp.exists():
                rp.unlink()
            return True

    def save_results(self, task_id: str, results: list[SkillResult]) -> None:
        with self._lock:
            self._results[task_id] = results
            self._results_path(task_id).write_text(
                json.dumps([r.model_dump() for r in results], indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def get_results(self, task_id: str) -> list[SkillResult]:
        with self._lock:
            return list(self._results.get(task_id, []))

    def set_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: float | None = None,
        completed_skills: int | None = None,
        error_message: str | None = None,
    ) -> ComplianceTask | None:
        with self._lock:
            task = self._cache.get(task_id)
            if task is None:
                return None
            task.status = status
            if progress is not None:
                task.progress = progress
            if completed_skills is not None:
                task.completed_skills = completed_skills
            if error_message is not None:
                task.error_message = error_message
            from datetime import datetime, timezone
            task.updated_at = datetime.now(timezone.utc).isoformat()
            self._task_path(task_id).write_text(
                task.model_dump_json(indent=2), encoding="utf-8"
            )
            return task


_user_store: UserStore | None = None
_task_store: TaskStore | None = None


def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        from backend.config import get_config
        cfg = get_config()
        _user_store = UserStore(data_dir=str(Path(cfg.storage.tasks_dir).parent))
    return _user_store


def get_task_store() -> TaskStore:
    global _task_store
    if _task_store is None:
        from backend.config import get_config
        cfg = get_config()
        _task_store = TaskStore(data_dir=cfg.storage.tasks_dir)
    return _task_store
