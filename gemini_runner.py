#!/usr/bin/env python3
import argparse
import json
import os
import queue
import random
import string
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RunnerConfig:
    task: str
    cwd: str
    cmd: str
    model: str
    mode: str
    timeout_seconds: int
    output_dir: str
    machine: bool
    human_stream: bool
    human_render: str
    resume_session: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{ts}-{suffix}"


def _build_args(cfg: RunnerConfig) -> List[str]:
    args: List[str] = ["--output-format", "stream-json"]
    mode = (cfg.mode or "default").strip().lower()
    if mode == "yolo":
        args.append("-y")
    elif mode in ("auto_edit", "autoedit"):
        args.extend(["--approval-mode", "auto_edit"])
    elif mode == "plan":
        args.extend(["--approval-mode", "plan"])

    if cfg.resume_session:
        args.extend(["--resume", cfg.resume_session])
    if cfg.model:
        args.extend(["-m", cfg.model])

    args.extend(["-p", cfg.task])
    return args


def _get_gemini_cmd() -> str:
    """Get the correct Gemini CLI command for the current platform."""
    import platform
    import shutil
    
    # First try to find gemini in PATH
    gemini_path = shutil.which("gemini")
    if gemini_path:
        return gemini_path
    
    # On Windows, try with .cmd extension
    if platform.system() == "Windows":
        gemini_cmd = shutil.which("gemini.cmd")
        if gemini_cmd:
            return gemini_cmd
    
    # Fallback to just "gemini" and let subprocess handle the error
    return "gemini"


def _safe_json_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a JSON line safely, returning None if invalid or not a dict."""
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
        if not isinstance(obj, dict):
            return None
        return obj
    except json.JSONDecodeError:
        return None


def _format_tool_input(params: Any) -> str:
    if isinstance(params, dict):
        try:
            return json.dumps(params, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(params)
    return ""


def _compact_human_print(kind: str, message: str) -> None:
    # Human-only rendering: keep terminal output compact.
    sys.stdout.write(f"\r[{kind}] {message[:120]}".ljust(140))
    sys.stdout.flush()


def _line_human_print(kind: str, message: str) -> None:
    print(f"[{kind}] {message}")


def run_task(cfg: RunnerConfig) -> Dict[str, Any]:
    run_id = _run_id()
    out_root = Path(cfg.output_dir).resolve()
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    events_path = run_dir / "events.jsonl"
    stderr_path = run_dir / "stderr.txt"
    stdout_text_path = run_dir / "stdout.txt"
    result_path = run_dir / "result.json"
    meta_path = run_dir / "meta.json"

    args = _build_args(cfg)
    timeout_seconds = cfg.timeout_seconds if cfg.timeout_seconds > 0 else 1800
    
    # Auto-detect correct gemini command if default is used
    cmd_executable = cfg.cmd if cfg.cmd != "gemini" else _get_gemini_cmd()
    cmd = [cmd_executable] + args

    start_ts = _utc_now()
    start_time = time.time()

    text_parts: List[str] = []
    tool_uses: List[Dict[str, Any]] = []
    errors: List[str] = []
    session_id = cfg.resume_session or ""
    status = "ok"

    stdout_q: "queue.Queue[Optional[str]]" = queue.Queue()
    stderr_q: "queue.Queue[Optional[str]]" = queue.Queue()
    stderr_parts: List[str] = []
    raw_event_count = 0

    def read_stream(pipe, out_q: "queue.Queue[Optional[str]]"):
        try:
            for line in pipe:
                out_q.put(line)
        finally:
            out_q.put(None)

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cfg.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        status = "spawn_error"
        errors.append(f"spawn failed: {exc}")
        proc = None

    if proc is not None and proc.stdout is not None and proc.stderr is not None:
        t_out = threading.Thread(target=read_stream, args=(proc.stdout, stdout_q), daemon=False)
        t_err = threading.Thread(target=read_stream, args=(proc.stderr, stderr_q), daemon=False)
        t_out.start()
        t_err.start()

        out_done = False
        err_done = False

        timeout_draining_until = 0.0
        with events_path.open("w", encoding="utf-8", newline="\n") as events_file:
            while True:
                now = time.time()
                if timeout_draining_until == 0.0 and timeout_seconds > 0 and (now - start_time) > timeout_seconds:
                    status = "timeout"
                    errors.append(f"timeout after {timeout_seconds}s")
                    proc.kill()
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()  # Force kill if needed
                    # Drain pending stdout/stderr briefly so diagnostics are not lost.
                    timeout_draining_until = time.time() + 0.5

                got_data = False

                try:
                    line = stdout_q.get(timeout=0.05)
                    got_data = True
                    if line is None:
                        out_done = True
                    else:
                        obj = _safe_json_line(line)
                        if obj is not None:
                            events_file.write(json.dumps(obj, ensure_ascii=False) + "\n")
                            raw_event_count += 1
                            et = str(obj.get("type", ""))
                            if et == "init":
                                sid = obj.get("session_id")
                                if isinstance(sid, str) and sid:
                                    session_id = sid
                                    if cfg.human_stream and not cfg.machine:
                                        msg = f"session={sid}"
                                        if cfg.human_render == "compact":
                                            _compact_human_print("init", msg)
                                        else:
                                            _line_human_print("init", msg)
                            elif et == "message":
                                role = str(obj.get("role", ""))
                                content = obj.get("content")
                                if role != "user" and isinstance(content, str) and content:
                                    text_parts.append(content)
                                    if cfg.human_stream and not cfg.machine:
                                        if cfg.human_render == "compact":
                                            _compact_human_print("message", content)
                                        else:
                                            _line_human_print("message", content)
                            elif et == "tool_use":
                                tool_name = str(obj.get("tool_name", "tool"))
                                params = obj.get("parameters", {})
                                item = {
                                    "name": tool_name,
                                    "input": _format_tool_input(params),
                                    "status": "started",
                                }
                                tool_uses.append(item)
                                if cfg.human_stream and not cfg.machine:
                                    msg = f"{tool_name}"
                                    if cfg.human_render == "compact":
                                        _compact_human_print("tool", msg)
                                    else:
                                        _line_human_print("tool", msg)
                            elif et == "tool_result":
                                if tool_uses:
                                    tool_uses[-1]["status"] = str(obj.get("status", "done"))
                            elif et == "error":
                                msg = str(obj.get("message", "unknown error"))
                                errors.append(msg)
                                status = "error"
                                if cfg.human_stream and not cfg.machine:
                                    if cfg.human_render == "compact":
                                        _compact_human_print("error", msg)
                                    else:
                                        _line_human_print("error", msg)
                            elif et == "result":
                                if str(obj.get("status", "")).lower() == "error":
                                    status = "error"
                except queue.Empty:
                    pass

                while True:
                    try:
                        err_line = stderr_q.get_nowait()
                        got_data = True
                        if err_line is None:
                            err_done = True
                            break
                        stderr_parts.append(err_line)
                    except queue.Empty:
                        break

                polled = proc.poll()
                if polled is not None and out_done and err_done:
                    break

                if timeout_draining_until > 0.0 and time.time() >= timeout_draining_until:
                    break

                if not got_data:
                    time.sleep(0.01)

        try:
            rc = proc.wait(timeout=2) if proc.poll() is None else (proc.returncode if proc.returncode is not None else 0)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait(timeout=1)
        t_out.join(timeout=1)
        t_err.join(timeout=1)
        if rc and status == "ok":
            status = "error"
            errors.append(f"process exited with code {rc}")
    else:
        rc = -1

    final_text = "".join(text_parts).strip()
    if status == "ok" and not final_text:
        status = "empty"

    stderr_text = "".join(stderr_parts)
    stderr_path.write_text(stderr_text, encoding="utf-8")
    stdout_text_path.write_text(final_text, encoding="utf-8")

    end_ts = _utc_now()
    duration_ms = int((time.time() - start_time) * 1000)

    result = {
        "run_id": run_id,
        "status": status,
        "session_id": session_id,
        "summary_text": final_text[:300],
        "final_text": final_text,
        "tool_uses": tool_uses,
        "errors": errors,
        "timing": {"start_ts": start_ts, "end_ts": end_ts, "duration_ms": duration_ms},
        "artifacts": {
            "events_jsonl": str(events_path),
            "stdout_txt": str(stdout_text_path),
            "stderr_txt": str(stderr_path),
        },
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "run_id": run_id,
        "cmd": cmd_executable,
        "args": args,
        "cwd": cfg.cwd,
        "machine": cfg.machine,
        "human_stream": cfg.human_stream,
        "human_render": cfg.human_render,
        "return_code": rc,
        "event_count": raw_event_count,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"result_path": str(result_path), "result": result}


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gemini isolated runner (machine-first).")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run-audit", help="Run one isolated Gemini audit task")
    run_p.add_argument("--task", required=True, help="Audit prompt to send to Gemini")
    run_p.add_argument("--cwd", default=".", help="Working directory")
    run_p.add_argument("--cmd", default="gemini", help="Gemini CLI command")
    run_p.add_argument("--model", default="", help="Model id")
    run_p.add_argument("--mode", default="default", choices=["default", "auto_edit", "yolo", "plan"])
    run_p.add_argument("--timeout-seconds", type=int, default=1800)
    run_p.add_argument("--output-dir", default=".gemini-runs")
    run_p.add_argument("--resume-session", default="")
    run_p.add_argument("--machine", action="store_true", help="Force machine protocol output")
    run_p.add_argument("--human-stream", action="store_true", help="Human-friendly stream output")
    run_p.add_argument("--human-render", choices=["compact", "full"], default="compact")

    run_alias = sub.add_parser("run", help="Alias of run-audit")
    run_alias.add_argument("--task", required=True)
    run_alias.add_argument("--cwd", default=".")
    run_alias.add_argument("--cmd", default="gemini")
    run_alias.add_argument("--model", default="")
    run_alias.add_argument("--mode", default="default", choices=["default", "auto_edit", "yolo", "plan"])
    run_alias.add_argument("--timeout-seconds", type=int, default=1800)
    run_alias.add_argument("--output-dir", default=".gemini-runs")
    run_alias.add_argument("--resume-session", default="")
    run_alias.add_argument("--machine", action="store_true")
    run_alias.add_argument("--human-stream", action="store_true")
    run_alias.add_argument("--human-render", choices=["compact", "full"], default="compact")

    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    ns = _parse_args(argv)
    if ns.timeout_seconds <= 0:
        ns.timeout_seconds = 1800
    machine = True
    if ns.human_stream and not ns.machine:
        machine = False

    cfg = RunnerConfig(
        task=ns.task,
        cwd=ns.cwd,
        cmd=ns.cmd,
        model=ns.model,
        mode=ns.mode,
        timeout_seconds=ns.timeout_seconds,
        output_dir=ns.output_dir,
        machine=machine,
        human_stream=bool(ns.human_stream),
        human_render=ns.human_render,
        resume_session=ns.resume_session,
    )
    out = run_task(cfg)
    result_path = out["result_path"]
    status = out["result"]["status"]

    if machine:
        print(f"RESULT_JSON={result_path}")
    else:
        print("\n")
        print(f"status={status}")
        print(f"result_json={result_path}")

    return 0 if status in ("ok", "empty") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

