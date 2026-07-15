"""Auto-discover compliance skills from compliance_skills/ directory."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from backend.logger import get_logger

logger = get_logger(__name__)

SKILLS_DIR_ENV = "COMPLIANCE_SKILLS_DIR"


@dataclass
class SkillEntry:
    name: str
    label: str
    description: str = ""
    enabled: bool = True
    path: Path | None = None
    skill_md_path: str = ""

    def to_info_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "enabled": self.enabled,
        }


def _find_skills_dir() -> Path:
    env_dir = os.environ.get(SKILLS_DIR_ENV)
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p.resolve()
    return Path(__file__).resolve().parents[1] / "compliance_skills"


_registry: dict[str, SkillEntry] | None = None


def get_registry(refresh: bool = False) -> dict[str, SkillEntry]:
    global _registry
    if _registry is not None and not refresh:
        return dict(_registry)

    skills_dir = _find_skills_dir()
    result: dict[str, SkillEntry] = {}

    if not skills_dir.is_dir():
        logger.warning("Compliance skills directory not found: %s", skills_dir)
        _registry = result
        return result

    for item in sorted(skills_dir.iterdir()):
        if not item.is_dir():
            continue
        yaml_path = item / "checker.yaml"
        skill_md = item / "SKILL.md"
        if not yaml_path.is_file():
            continue

        try:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("Failed to parse %s: %s", yaml_path, e)
            continue

        name = raw.get("name", item.name)
        if not raw.get("enabled", True):
            continue

        entry = SkillEntry(
            name=name,
            label=raw.get("label", name),
            description=raw.get("description", ""),
            enabled=True,
            path=item,
            skill_md_path=str(skill_md) if skill_md.is_file() else "",
        )
        result[name] = entry

    _registry = result
    logger.info("Loaded %d compliance skill(s): %s", len(result), list(result.keys()))
    return dict(result)
