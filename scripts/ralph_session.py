#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_COMPLETION_PROMISE = "<promise>COMPLETE</promise>"
DEFAULT_MAX_ITERATIONS = 20


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def state_path(root: Path) -> Path:
    return root / ".codex-loop" / "ralph-loop.json"


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def all_tasks_complete(root: Path) -> bool:
    tasks_path = root / ".codex-loop" / "tasks.json"
    if not tasks_path.exists():
        return False
    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return False
    return all(str(task.get("status", "")).lower() in {"done", "completed", "complete", "skipped"} for task in tasks)


def refresh_context(root: Path, source: str) -> None:
    script = root / "scripts" / "context_engine.py"
    if not script.exists():
        return
    subprocess.run(
        [sys.executable, str(script), "refresh", "--source", source],
        cwd=root,
        capture_output=True,
        text=True,
    )


def cmd_start(args: argparse.Namespace) -> int:
    root = project_root()
    path = state_path(root)
    current = load_state(path)
    if current.get("active") and not args.force:
        print("An active Ralph loop already exists. Use --force to replace it.", file=sys.stderr)
        return 2

    timestamp = now_iso()
    payload: dict[str, Any] = {
        "version": 2,
        "active": True,
        "status": "active",
        "prompt": args.prompt.strip(),
        "completionPromise": args.completion_promise,
        "maxIterations": args.max_iterations,
        "currentIteration": 0,
        "startedAt": timestamp,
        "updatedAt": timestamp,
        "lastAssistantMessage": "",
        "lastContinuationPrompt": "",
        "requireTaskCompletion": all_tasks_complete(root) or (root / ".codex-loop" / "tasks.json").exists(),
    }
    write_state(path, payload)
    refresh_context(root, "ralph-session-start")

    print("Ralph loop armed.")
    print(f"- state: {path}")
    print(f"- completion promise: {payload['completionPromise']}")
    print(f"- max iterations: {payload['maxIterations']}")
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    root = project_root()
    path = state_path(root)
    current = load_state(path)
    if not current.get("active"):
        print("No active Ralph loop.")
        return 0

    current["active"] = False
    current["status"] = "cancelled"
    current["cancelledAt"] = now_iso()
    current["updatedAt"] = current["cancelledAt"]
    if args.reason:
        current["cancelReason"] = args.reason
    write_state(path, current)
    refresh_context(root, "ralph-session-cancel")

    print("Cancelled the active Ralph loop.")
    print(f"- state: {path}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = project_root()
    path = state_path(root)
    current = load_state(path)
    if args.json:
        print(json.dumps(current, ensure_ascii=False, indent=2))
        return 0
    if not current:
        print("No Ralph loop state file yet.")
        return 0

    print(f"active: {bool(current.get('active'))}")
    print(f"status: {current.get('status', 'unknown')}")
    print(f"current iteration: {current.get('currentIteration', 0)}")
    print(f"completion promise: {current.get('completionPromise', DEFAULT_COMPLETION_PROMISE)}")
    print(f"max iterations: {current.get('maxIterations', DEFAULT_MAX_ITERATIONS)}")
    print(f"require task completion: {bool(current.get('requireTaskCompletion'))}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the hook-native Ralph loop state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start or replace the active Ralph loop")
    start.add_argument("--prompt", required=True, help="Original task prompt to keep replaying")
    start.add_argument("--completion-promise", default=DEFAULT_COMPLETION_PROMISE, help="String that marks real completion")
    start.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS, help="Maximum Stop-hook continuations before allowing the turn to end")
    start.add_argument("--force", action="store_true", help="Replace an existing active loop")
    start.set_defaults(func=cmd_start)

    cancel = subparsers.add_parser("cancel", help="Cancel the active Ralph loop")
    cancel.add_argument("--reason", help="Optional cancellation reason")
    cancel.set_defaults(func=cmd_cancel)

    status = subparsers.add_parser("status", help="Show the active Ralph loop state")
    status.add_argument("--json", action="store_true", help="Print raw JSON")
    status.set_defaults(func=cmd_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
