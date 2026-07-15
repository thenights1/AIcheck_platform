"""Agent command handlers — dispatches server commands."""

from __future__ import annotations

import asyncio
from pathlib import Path

TASK_MANAGER: dict = {}  # task_id -> (asyncio.Task, asyncio.Event)


async def handle_task(msg: dict, config, task_manager, reporter) -> dict | None:
    """Handle a 'task' command from the server."""
    task_id = msg["task_id"]
    target_folder = msg.get("target_folder", "")
    skill_names = msg.get("skills", [])
    task_name = msg.get("task_name", "Compliance Task")

    # Resolve skills from local compliance_skills/ directory
    skills, _ = _resolve_local_skills(skill_names)

    print(f"\n{'='*60}")
    print(f"Received task: {task_name}")
    print(f"  Task ID: {task_id}")
    print(f"  Target:  {target_folder}")
    print(f"  Skills:  {[s['name'] for s in skills]}")
    print(f"{'='*60}\n")

    if not skills:
        await reporter.send_progress(task_id, "error", error_message=f"No valid skills found")
        await reporter.finish_task(task_id, "error", error_message="No valid skills")
        return None

    cancel_event = asyncio.Event()

    async def _run():
        from agent.runner import run_compliance_task
        await run_compliance_task(
            task_id=task_id,
            task_name=task_name,
            target_folder=target_folder,
            skills=skills,
            skills_dir="",
            reporter=reporter,
            config=config,
            cancel_event=cancel_event,
        )

    task = asyncio.create_task(_run())
    TASK_MANAGER[task_id] = (task, cancel_event)

    return None


async def handle_stop(msg: dict, config, task_manager, reporter) -> dict | None:
    """Handle a 'stop' command from the server."""
    task_id = msg["task_id"]
    print(f"Received stop command for task: {task_id}")

    entry = TASK_MANAGER.pop(task_id, None)
    if entry is not None:
        _, cancel_event = entry
        cancel_event.set()
        await reporter.send_progress(task_id, "cancelled")
        await reporter.finish_task(task_id, "cancelled")
    return None


async def handle_resume(msg: dict, config, task_manager, reporter) -> dict | None:
    """Handle a 'resume' command — re-run the task."""
    return await handle_task(msg, config, task_manager, reporter)


async def handle_config(msg: dict, config, task_manager, reporter) -> dict | None:
    """Handle a 'config' update from the server."""
    from agent.config import apply_remote_config
    remote = msg.get("config", {})
    apply_remote_config(config, remote)
    print(f"Config updated from server")
    return None


def _resolve_local_skills(skill_names: list[str]) -> tuple[list[dict], Path | None]:
    """Look up skills from local compliance_skills/ directory on the agent machine."""
    repo_root = Path(__file__).resolve().parents[1]
    skills_dir = repo_root / "compliance_skills"
    if not skills_dir.is_dir():
        return [], None

    import yaml

    result: list[dict] = []
    for name in skill_names:
        skill_dir = skills_dir / name
        yaml_path = skill_dir / "checker.yaml"
        skill_md = skill_dir / "SKILL.md"
        if not yaml_path.is_file():
            continue
        try:
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        except Exception:
            raw = {}
        result.append({
            "name": name,
            "label": raw.get("label", name),
            "description": raw.get("description", ""),
            "skill_md_path": str(skill_md) if skill_md.is_file() else "",
        })

    return result, skills_dir


COMMAND_HANDLERS = {
    "task": handle_task,
    "stop": handle_stop,
    "resume": handle_resume,
    "config": handle_config,
}
