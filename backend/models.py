"""Pydantic models for the compliance audit system."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    ERROR = "error"


class SkillResultStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    PENDING = "pending"
    RUNNING = "running"


class User(BaseModel):
    user_id: str
    username: str
    role: str = "user"


class SkillInfo(BaseModel):
    name: str
    label: str
    description: str = ""
    enabled: bool = True


class ComplianceTask(BaseModel):
    task_id: str
    task_name: str
    target_folder: str
    skills: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    total_skills: int = 0
    completed_skills: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_message: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    user_id: str | None = None


class SkillResult(BaseModel):
    skill_name: str
    skill_label: str = ""
    status: SkillResultStatus = SkillResultStatus.PENDING
    output: str = ""
    result_detail: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None


class TaskSummary(BaseModel):
    task_id: str
    task_name: str
    target_folder: str
    status: TaskStatus
    progress: float
    total_skills: int
    completed_skills: int
    created_at: str
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    agent_name: str | None = None


class TaskCreateRequest(BaseModel):
    task_name: str
    target_folder: str
    skills: list[str]
    agent_id: str = ""


class AgentRemoteConfig(BaseModel):
    opencode: dict[str, Any] = Field(default_factory=dict)
    llm_api: dict[str, Any] = Field(default_factory=dict)


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    ip: str = ""
    last_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    online: bool = True
    user_id: str = ""
