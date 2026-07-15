"""Agent configuration — loaded from agent.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class OpenCodeConfig:
    tool: str = "opencode"
    executable: str = "opencode"
    model: str = ""
    timeout: int = 600
    max_retries: int = 1


@dataclass
class LLMApiConfig:
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout: int = 300
    max_retries: int = 3
    temperature: float = 0.1
    stream: bool = False


@dataclass
class AgentConfig:
    server_url: str = "http://localhost:8000"
    agent_name: str = ""
    no_proxy: str = ""
    opencode: OpenCodeConfig = field(default_factory=OpenCodeConfig)
    llm_api: LLMApiConfig = field(default_factory=LLMApiConfig)


def load_config(path: Path | None = None) -> AgentConfig:
    if path is None:
        candidates = [
            Path("agent.yaml"),
            Path(__file__).resolve().parents[1] / "agent.yaml",
        ]
        for p in candidates:
            if p.is_file():
                path = p
                break

    if path is None or not path.is_file():
        return AgentConfig()

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cfg = AgentConfig()
    if "server_url" in raw:
        cfg.server_url = raw["server_url"]
    if "agent_name" in raw:
        cfg.agent_name = raw["agent_name"]
    if "no_proxy" in raw:
        cfg.no_proxy = raw.get("no_proxy", "")
    if "opencode" in raw:
        oc = raw["opencode"]
        cfg.opencode = OpenCodeConfig(**{k: v for k, v in oc.items() if k in OpenCodeConfig.__dataclass_fields__})
    if "llm_api" in raw:
        la = raw["llm_api"]
        cfg.llm_api = LLMApiConfig(**{k: v for k, v in la.items() if k in LLMApiConfig.__dataclass_fields__})
    return cfg


def apply_remote_config(config: AgentConfig, remote: dict) -> None:
    if "opencode" in remote:
        oc = remote["opencode"]
        for k, v in oc.items():
            if k in OpenCodeConfig.__dataclass_fields__:
                setattr(config.opencode, k, v)
    if "llm_api" in remote:
        la = remote["llm_api"]
        for k, v in la.items():
            if k in LLMApiConfig.__dataclass_fields__:
                setattr(config.llm_api, k, v)


def remote_config_dict(config: AgentConfig) -> dict:
    return {
        "opencode": {
            "tool": config.opencode.tool,
            "executable": config.opencode.executable,
            "model": config.opencode.model,
            "timeout": config.opencode.timeout,
            "max_retries": config.opencode.max_retries,
        },
        "llm_api": {
            "enabled": config.llm_api.enabled,
            "base_url": config.llm_api.base_url,
            "model": config.llm_api.model,
            "timeout": config.llm_api.timeout,
        },
    }


def apply_network_env(config: AgentConfig) -> None:
    if config.no_proxy:
        os.environ["no_proxy"] = config.no_proxy
        os.environ["NO_PROXY"] = config.no_proxy
