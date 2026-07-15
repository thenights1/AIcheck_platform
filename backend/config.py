"""Configuration loaded from config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    port: int = 8000
    host: str = "0.0.0.0"


@dataclass
class StorageConfig:
    tasks_dir: str = "data/tasks"


@dataclass
class AuthConfig:
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"
    secret_key: str = "compliance-audit-secret-key-change-me"
    token_expire_hours: int = 24


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
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    opencode: OpenCodeConfig = field(default_factory=OpenCodeConfig)
    llm_api: LLMApiConfig = field(default_factory=LLMApiConfig)


_config: AppConfig | None = None


def _find_config() -> Path | None:
    candidates = [
        Path(os.environ.get("CONFIG_PATH", "")),
        Path("config.yaml"),
        Path(__file__).resolve().parents[1] / "config.yaml",
    ]
    for p in candidates:
        if p.is_file():
            return p.resolve()
    return None


def load_config(path: str | Path | None = None) -> AppConfig:
    global _config
    if path:
        p = Path(path)
    else:
        p = _find_config()
    if p is None or not p.is_file():
        return AppConfig()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    cfg = AppConfig()
    if "server" in raw:
        cfg.server = ServerConfig(**{k: v for k, v in raw["server"].items() if k in ServerConfig.__dataclass_fields__})
    if "storage" in raw:
        cfg.storage = StorageConfig(**{k: v for k, v in raw["storage"].items() if k in StorageConfig.__dataclass_fields__})
    if "auth" in raw:
        cfg.auth = AuthConfig(**{k: v for k, v in raw["auth"].items() if k in AuthConfig.__dataclass_fields__})
    if "opencode" in raw:
        cfg.opencode = OpenCodeConfig(**{k: v for k, v in raw["opencode"].items() if k in OpenCodeConfig.__dataclass_fields__})
    if "llm_api" in raw:
        cfg.llm_api = LLMApiConfig(**{k: v for k, v in raw["llm_api"].items() if k in LLMApiConfig.__dataclass_fields__})
    _config = cfg
    return cfg


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config
