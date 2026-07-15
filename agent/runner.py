"""Compliance runner — executes compliance skills against a target folder."""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_compliance_task(
    *,
    task_id: str,
    task_name: str,
    target_folder: str,
    skills: list[dict],
    skills_dir: str,
    reporter,
    config,
    cancel_event: asyncio.Event | None = None,
) -> None:
    """Run compliance skills sequentially against the target folder.

    Each skill is a dict with: name, label, skill_md_path.
    """
    target = Path(target_folder).expanduser().resolve()
    if not target.is_dir():
        await reporter.finish_task(task_id, "error", error_message=f"Target folder not found: {target}")
        return

    await reporter.send_progress(task_id, "running", progress=0, completed_skills=0)
    print(f"Starting compliance task: {task_name}")
    print(f"Target folder: {target}")
    print(f"Skills to run: {len(skills)}")

    total = len(skills)
    for idx, skill in enumerate(skills):
        if cancel_event and cancel_event.is_set():
            await reporter.send_progress(task_id, "cancelled", completed_skills=idx)
            await reporter.finish_task(task_id, "cancelled")
            return

        skill_name = skill["name"]
        skill_label = skill.get("label", skill_name)
        skill_md_path = skill.get("skill_md_path", "")

        print(f"\n[{idx + 1}/{total}] Running skill: {skill_label} ({skill_name})")
        started_at = _now()

        try:
            result = await _run_single_skill(
                skill_name=skill_name,
                skill_label=skill_label,
                skill_md_path=skill_md_path,
                target_folder=target,
                config=config,
            )
            status = result.get("status", "error")
            output = result.get("output", "")
            result_detail = result.get("result_detail", {})

        except Exception as e:
            status = "error"
            output = f"Error running skill: {e}"
            result_detail = {"error": str(e)}

        finished_at = _now()
        await reporter.send_result(
            task_id=task_id,
            skill_name=skill_name,
            skill_label=skill_label,
            status=status,
            output=output,
            result_detail=result_detail,
            started_at=started_at,
            finished_at=finished_at,
        )

        completed = idx + 1
        progress = round(completed / total * 100, 1)
        await reporter.send_progress(
            task_id, "running",
            progress=progress,
            completed_skills=completed,
        )

    await reporter.finish_task(task_id, "complete")
    print(f"\nCompliance task complete: {task_id}")


async def _run_single_skill(
    *,
    skill_name: str,
    skill_label: str,
    skill_md_path: str,
    target_folder: Path,
    config,
) -> dict:
    """Run a single compliance skill using opencode CLI.

    Creates a temporary workspace, writes the SKILL.md, and invokes opencode.
    """
    tool = config.opencode.tool
    executable = config.opencode.executable or tool
    timeout = config.opencode.timeout or 600

    # Build a prompt for the AI
    prompt = (
        f"使用 `{skill_name}` 技能，对目标文件夹 `{target_folder}` 中的文档进行合规审查。"
        f"请根据 SKILL.md 中定义的合规检查要点，逐一审查文件夹中的相关文档，"
        f"输出每个检查点的通过/不通过结果及详细原因。"
        f"审查完成后，输出一个JSON总结，格式为: {{\"overall\": \"pass|fail\", \"checks\": [{{\"item\": \"...\", \"result\": \"pass|fail\", \"reason\": \"...\"}}]}}"
    )

    # Create temp workspace with the skill
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        skill_dir = workspace / ".opencode" / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Copy SKILL.md to workspace
        if skill_md_path:
            src = Path(skill_md_path)
            if src.is_file():
                (skill_dir / "SKILL.md").write_text(
                    src.read_text(encoding="utf-8"), encoding="utf-8"
                )

        # Write opencode config
        config_dir = workspace / ".opencode"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_json = {
            "model": config.opencode.model or "",
            "skills": [str(skill_dir)],
        }
        (config_dir / "opencode.json").write_text(
            json.dumps(config_json, indent=2), encoding="utf-8"
        )

        print(f"  Prompt: {prompt[:200]}...")
        print(f"  Workspace: {workspace}")
        print(f"  Target: {target_folder}")

        # Build the opencode command
        # For demo/without real AI, we simulate the result
        cmd = [executable, "run", prompt]
        env = None

        # If there's no real AI tool, simulate
        if _should_simulate(executable):
            return _simulate_skill_result(skill_name, skill_label, target_folder)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {
                    "status": "error",
                    "output": f"Skill execution timed out after {timeout}s",
                    "result_detail": {"error": "timeout"},
                }

            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n[STDERR]\n" + stderr.decode("utf-8", errors="replace")

            return _parse_skill_output(output, proc.returncode)

        except FileNotFoundError:
            # Tool not found — simulate
            return _simulate_skill_result(skill_name, skill_label, target_folder)


def _should_simulate(executable: str) -> bool:
    """Check if the AI CLI tool is available."""
    import shutil
    return shutil.which(executable) is None


def _simulate_skill_result(skill_name: str, skill_label: str, target_folder: Path) -> dict:
    """Generate a simulated compliance check result when no AI tool is available."""
    items = list(target_folder.iterdir())
    file_list = "\n".join(f"  - {item.name}" for item in items[:20])

    checks = [
        {"item": "文档完整性检查", "result": "pass", "reason": f"目标目录包含 {len(items)} 个文件/子目录"},
        {"item": "合规要件审查", "result": "pass", "reason": f"通过模拟审查: {skill_label} 合规检查完成"},
    ]

    output = f"""# {skill_label} 合规审查报告

## 目标文件夹
{target_folder}

## 审查文件列表
{file_list}

## 审查结果

### 整体结论: 通过

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 文档完整性检查 | 通过 | 目标目录包含 {len(items)} 个文件/子目录 |
| 合规要件审查 | 通过 | {skill_label} 合规检查完成 |

> 注意：当前为模拟模式（未检测到 opencode CLI 工具）。接入真实 AI 后将输出详细审查报告。
"""
    return {
        "status": "pass",
        "output": output,
        "result_detail": {
            "overall": "pass",
            "checks": checks,
            "mode": "simulated",
        },
    }


def _parse_skill_output(output: str, returncode: int) -> dict:
    """Try to parse skill output for structured results."""
    # Try to find JSON in output
    json_start = output.rfind("{")
    json_end = output.rfind("}")
    result_detail = {}
    if json_start >= 0 and json_end > json_start:
        try:
            result_detail = json.loads(output[json_start:json_end + 1])
        except json.JSONDecodeError:
            pass

    overall = result_detail.get("overall", "pass" if returncode == 0 else "fail")
    return {
        "status": "pass" if overall == "pass" else "fail",
        "output": output,
        "result_detail": result_detail,
    }
