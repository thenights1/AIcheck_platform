"""Agent daemon — connects to ComplianceAudit backend, waits for commands."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ComplianceAudit Agent Daemon")
    p.add_argument("--server", default="", help="Backend server URL (default: http://localhost:8000)")
    p.add_argument("--name", default="", help="Agent display name")
    p.add_argument("--config", default="", help="Path to agent.yaml")
    return p.parse_args()


async def _handle_command(msg: dict, config, task_manager, reporter) -> dict | None:
    from agent.server import COMMAND_HANDLERS
    cmd_type = msg.get("type", "")
    handler = COMMAND_HANDLERS.get(cmd_type)
    if handler is None:
        print(f"Unknown command type: {cmd_type}")
        return None
    return await handler(msg, config, task_manager, reporter)


async def _ws_loop(config, task_manager, reporter) -> None:
    import websockets

    name = config.agent_name or socket.gethostname()
    ws_url = config.server_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = ws_url.rstrip("/") + "/api/agent/ws"
    ping_interval = _env_int("COMPLIANCE_WS_PING_INTERVAL", 30)
    ping_timeout = _env_int("COMPLIANCE_WS_PING_TIMEOUT", 120)
    heartbeat_interval = _env_int("COMPLIANCE_AGENT_HEARTBEAT_INTERVAL", 30)

    reconnect_delay = 2

    while True:
        try:
            print(f"Connecting to {ws_url} ...")
            async with websockets.connect(
                ws_url,
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
            ) as ws:
                from agent.config import remote_config_dict

                hello_msg = {
                    "type": "hello",
                    "name": name,
                    "config": remote_config_dict(config),
                    "owner_token": config.owner_token,
                }
                await ws.send(json.dumps(hello_msg))

                welcome_raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
                welcome = json.loads(welcome_raw)

                if welcome.get("type") != "welcome":
                    print(f"Unexpected handshake response: {welcome}")
                    continue

                agent_id = welcome["agent_id"]
                reporter.set_agent_id(agent_id)

                if welcome.get("config"):
                    from agent.config import apply_remote_config
                    apply_remote_config(config, welcome["config"])
                    print("Config received from server")

                reconnect_delay = 2
                print(f"  Connected. Agent ID: {agent_id}")
                print()

                loop = asyncio.get_running_loop()
                command_queue: asyncio.Queue = asyncio.Queue()

                async def _heartbeat():
                    while True:
                        await asyncio.sleep(heartbeat_interval)
                        await ws.send(json.dumps({"type": "heartbeat"}))

                async def _command_worker():
                    while True:
                        msg = await command_queue.get()
                        if msg is None:
                            return
                        try:
                            response = await _handle_command(msg, config, task_manager, reporter)
                            if response:
                                await ws.send(json.dumps(response))
                        except Exception as e:
                            print(f"Error handling command: {e}")

                heartbeat_task = asyncio.create_task(_heartbeat())
                worker_task = asyncio.create_task(_command_worker())

                try:
                    async for raw_msg in ws:
                        try:
                            msg = json.loads(raw_msg)
                        except Exception as e:
                            print(f"Error parsing server message: {e}")
                            continue
                        if msg.get("type") == "heartbeat_ack":
                            continue
                        await command_queue.put(msg)
                finally:
                    heartbeat_task.cancel()
                    await command_queue.put(None)
                    worker_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    try:
                        await worker_task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            print(f"Connection lost: {e}. Reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


async def _main() -> None:
    args = _parse_args()

    from agent.config import load_config
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    if args.server:
        config.server_url = args.server
    if args.name:
        config.agent_name = args.name

    name = config.agent_name or socket.gethostname()

    print("ComplianceAudit Agent Daemon")
    print(f"  Name    : {name}")
    print(f"  Server  : {config.server_url}")
    print()

    from agent.reporter import Reporter
    reporter = Reporter(config.server_url)
    reporter.set_agent_name(name)

    task_manager = {}

    try:
        await _ws_loop(config, task_manager, reporter)
    finally:
        await reporter.close()


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
