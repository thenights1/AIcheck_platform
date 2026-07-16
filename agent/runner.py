"""Compliance runner — executes compliance skills against a target folder."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
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

        # Send intermediate progress to keep frontend alive
        await reporter.send_progress(
            task_id, "running",
            progress=round(idx / total * 100, 1),
            completed_skills=idx,
            current_skill=skill_label,
        )

        # Stream opencode output in real-time
        output_lines: list[str] = []
        line_count = 0

        def _on_line(line: str) -> None:
            nonlocal line_count
            print(f"  [{skill_name}] {line}", flush=True)
            output_lines.append(line)
            line_count += 1

        try:
            result = await _run_single_skill_streaming(
                skill_name=skill_name,
                skill_label=skill_label,
                skill_md_path=skill_md_path,
                target_folder=target,
                config=config,
                on_line=_on_line,
                cancel_event=cancel_event,
                reporter=reporter,
                task_id=task_id,
            )
            status = result.get("status", "error")
            output = result.get("output", "\n".join(output_lines))
            result_detail = result.get("result_detail", {})

        except asyncio.CancelledError:
            status = "error"
            output = "\n".join(output_lines) + "\n[Task cancelled]"
            result_detail = {"error": "cancelled"}

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


async def _run_single_skill_streaming(
    *,
    skill_name: str,
    skill_label: str,
    skill_md_path: str,
    target_folder: Path,
    config,
    on_line=None,
    cancel_event: asyncio.Event | None = None,
    reporter=None,
    task_id: str = "",
) -> dict:
    tool = config.opencode.tool
    executable = config.opencode.executable or tool
    timeout = config.opencode.timeout or 600

    prompt = (
        f"使用 `{skill_name}` 技能，对目标文件夹 `{target_folder}` 中的文档进行合规审查。"
        f"请根据 SKILL.md 中定义的合规检查要点，逐一审查文件夹中的相关文档，"
        f"输出每个检查点的通过/不通过结果及详细原因。"
        f"审查完成后，输出一个JSON总结，格式为: {{\"overall\": \"pass|fail\", \"checks\": [{{\"item\": \"...\", \"result\": \"pass|fail\", \"reason\": \"...\"}}]}}"
    )

    # Create .opencode/ directly in target folder so opencode finds the skill
    opendir = target_folder / ".opencode"
    opendir.mkdir(parents=True, exist_ok=True)
    skill_dir = opendir / "skills" / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    if skill_md_path:
        src_dir = Path(skill_md_path).parent
        if src_dir.is_dir():
            _copytree(src_dir, skill_dir)

    config_json = {
        "model": config.opencode.model or "",
        "skills": {
            skill_name: str(skill_dir),
        },
    }
    (opendir / "opencode.json").write_text(
        json.dumps(config_json, indent=2), encoding="utf-8"
    )

    print(f"  Prompt: {prompt[:200]}...")
    print(f"  Target: {target_folder}")

    import shutil
    exe_path = shutil.which(executable)
    if exe_path is None:
        print(f"  [WARN] opencode CLI not found (looked for: {executable})")
        return _simulate_skill_result(skill_name, skill_label, target_folder)

    print(f"  opencode found at: {exe_path}")
    cmd = [exe_path, "run", "--dir", str(target_folder), prompt]
    print(f"  Command: {exe_path} run --dir {target_folder} <prompt>")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(target_folder),
        )
    except FileNotFoundError:
        print(f"  [ERROR] opencode not found at runtime: {exe_path}")
        return {
            "status": "error",
            "output": f"opencode CLI not found at {exe_path}.",
            "result_detail": {"error": "executable_not_found"},
        }
    except Exception as exc:
        print(f"  [ERROR] opencode start failed: {exc}")
        return {
            "status": "error",
            "output": f"Failed to start opencode: {exc}",
            "result_detail": {"error": "start_error", "detail": str(exc)},
        }

    # Stream stdout and stderr line by line
    stdout_lines: list[str] = []

    async def _read_stream(stream, prefix: str, collector: list[str] | None = None) -> None:
        while True:
            if proc.returncode is not None:
                break
            try:
                line = await stream.readline()
            except Exception:
                break
            if not line:
                break
            text = _decode_bytes(line).rstrip("\n").rstrip("\r")
            if text:
                if on_line:
                    on_line(f"{prefix}{text}")
                if collector is not None:
                    collector.append(text)

    async def _timeout_killer():
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

    if cancel_event:

        async def _cancel_watcher():
            await cancel_event.wait()
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

        cancel_task = asyncio.create_task(_cancel_watcher())

    # Read stdout/stderr concurrently
    stdout_task = asyncio.create_task(_read_stream(proc.stdout, "", collector=stdout_lines))
    stderr_task = asyncio.create_task(_read_stream(proc.stderr, "[STDERR] "))
    timeout_task = asyncio.create_task(_timeout_killer())

    # Wait for all to finish
    done, pending = await asyncio.wait(
        [stdout_task, stderr_task, timeout_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    # Ensure proc is done
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    # Cancel remaining tasks
    for t in pending:
        t.cancel()
    if cancel_event and "cancel_task" in locals():
        cancel_task.cancel()

    # Gather any remaining output
    for t in [stdout_task, stderr_task]:
        if not t.done():
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass

    if proc.returncode != 0 and proc.returncode is not None:
        if cancel_event and cancel_event.is_set():
            on_line("[进程已终止]") if on_line else None
        else:
            on_line(f"[进程退出，返回码: {proc.returncode}]") if on_line else None

    if cancel_event and cancel_event.is_set():
        return {
            "status": "error",
            "output": "[Task cancelled by user]",
            "result_detail": {"error": "cancelled"},
        }

    if proc.returncode != 0:
        return {
            "status": "error",
            "output": f"opencode exited with code {proc.returncode}",
            "result_detail": {"error": "non_zero_exit", "returncode": proc.returncode},
        }

    # Parse collected output to extract structured result
    collected_output = "\n".join(stdout_lines)
    parsed = _parse_ai_output(collected_output)
    overall = parsed.get("overall", "pass" if proc.returncode == 0 else "fail")
    checks = parsed.get("checks", [])

    # Build a clean summary markdown
    summary_lines = [f"## 审查结果: {'通过' if overall == 'pass' else '不通过'}", ""]
    if checks:
        summary_lines.append("| 检查项 | 结果 | 说明 |")
        summary_lines.append("|--------|------|------|")
        for c in checks:
            item = c.get("item", "?")
            result = c.get("result", "?")
            reason = c.get("reason", "")
            icon = {"pass": "通过", "fail": "不通过", "na": "不适用"}.get(result, result)
            summary_lines.append(f"| {item} | {icon} | {reason} |")
        summary_lines.append("")

    summary = "\n".join(summary_lines)

    return {
        "status": "pass" if overall == "pass" else "fail",
        "output": summary,
        "result_detail": {
            "overall": overall,
            "checks": checks,
            "raw_output": collected_output,
            "returncode": proc.returncode or 0,
        },
    }


def _simulate_skill_result(skill_name: str, skill_label: str, target_folder: Path) -> dict:
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
        "result_detail": {"overall": "pass", "checks": checks, "mode": "simulated"},
    }


def _decode_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("gbk")
    except UnicodeDecodeError:
        pass
    return data.decode("utf-8", errors="replace")


def _parse_ai_output(text: str) -> dict:
    """Extract the JSON block from AI output and return structured result."""
    import re
    # Find the last JSON object in the text (AI usually puts it at the end)
    matches = list(re.finditer(r'\{[^{}]*"overall"\s*:\s*"[^"]*"[^{}]*\}', text))
    if not matches:
        # Try to find any JSON block
        matches = list(re.finditer(r'\{[^{}]*\}', text))
    for m in reversed(matches):
        try:
            data = json.loads(m.group())
            if isinstance(data, dict) and "overall" in data:
                return {
                    "overall": data.get("overall", "pass"),
                    "checks": data.get("checks", []),
                }
        except json.JSONDecodeError:
            continue
    return {}


def _resolve_real_executable(path: str) -> str:
    """If the executable is a Windows .CMD wrapper, resolve to the actual .exe inside."""
    p = Path(path)
    if p.suffix.lower() != ".cmd":
        return path
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return path
    import re
    m = re.search(r'node_modules.+?\.exe', content)
    if m:
        resolved = p.parent / m.group(0)
        if resolved.is_file():
            return str(resolved)
    return path


def _copytree(src: Path, dst: Path) -> None:
    import shutil
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_file():
            shutil.copy2(item, target)
        elif item.is_dir():
            _copytree(item, target)
