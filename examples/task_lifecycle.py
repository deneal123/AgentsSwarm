"""
Пример полного цикла работы с задачей оркестратора.
Показывает живой вывод агентов в реальном времени во время выполнения.

Запуск:
    python examples/task_lifecycle.py
    python examples/task_lifecycle.py --host http://185.55.57.82:8009
    python examples/task_lifecycle.py --prompt "Покажи статус carter01"
    python examples/task_lifecycle.py --log run.log          # сохранить в файл
    python examples/task_lifecycle.py --log auto             # авто-имя по времени

Артефакты задачи сохраняются в logs/<task_id>/:
    run.log          — текстовый лог сессии
    map.png          — карта с метками роботов (если MapAnalyst запускался)
    route_<name>.png — визуализации маршрутов
    events.json      — все события задачи (сырые)
"""

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_HOST = "http://185.55.57.82:8009"
DEFAULT_PROMPT = "Покажи статус всех роботов и сводку по флоту"

# Sources whose messages are agent/system text worth showing live
_AGENT_SOURCES = {"agent", "agent-sdk", "orchestrator", "runner", "system"}

# Map source → display label
_SOURCE_LABELS = {
    "agent": "AGENT",
    "agent-sdk": "SDK",
    "orchestrator": "ORCH",
    "runner": "RUN",
    "system": "SYS",
}

# Status icons for plan steps
_STEP_ICONS = {
    "completed": "✓",
    "failed": "✗",
    "canceled": "⊘",
    "running": "►",
    "pending": "·",
}

# ANSI colors (disabled on Windows if not supported)
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"

_SOURCE_COLORS = {
    "agent": _GREEN,
    "agent-sdk": _CYAN,
    "orchestrator": _BLUE,
    "runner": _MAGENTA,
    "system": _DIM,
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


# ─── artifact dir ─────────────────────────────────────────────────────────────

_artifact_dir: Path | None = None


def _init_artifact_dir(task_id: str) -> Path:
    global _artifact_dir
    _artifact_dir = Path("logs") / task_id
    _artifact_dir.mkdir(parents=True, exist_ok=True)
    return _artifact_dir


def _save_image(filename: str, b64_data: str) -> Path | None:
    if not _artifact_dir:
        return None
    try:
        data = base64.b64decode(b64_data)
        path = _artifact_dir / filename
        path.write_bytes(data)
        return path
    except Exception:
        return None


# ─── log file ─────────────────────────────────────────────────────────────────

_log_file: Path | None = None


def _log(line: str) -> None:
    """Write a plain (no ANSI) line to the log file if configured."""
    if _log_file is None:
        return
    with _log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


def _out(line: str) -> None:
    """Print to stdout and mirror (stripped) to log file."""
    print(line)
    _log(_strip_ansi(line))


# ─── helpers ──────────────────────────────────────────────────────────────────

def _req(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"  HTTP {e.code} {e.reason}: {body_text}", file=sys.stderr)
        sys.exit(1)


def _section(title: str) -> None:
    _out(f"\n{_color('─' * 60, _DIM)}")
    _out(f"  {_color(title, _BOLD)}")
    _out(f"{_color('─' * 60, _DIM)}")


# ─── streaming state ──────────────────────────────────────────────────────────

_streaming_active: dict = {"agent": None}


def _flush_stream() -> None:
    if _streaming_active["agent"] is not None:
        print()
        _streaming_active["agent"] = None


# ─── image event handlers ─────────────────────────────────────────────────────

_saved_map = False
_saved_routes: set[str] = set()


def _handle_image_events(ev: dict) -> None:
    """Extract and save images from map_image / route_images events."""
    global _saved_map
    meta = ev.get("meta") or {}
    event_type = meta.get("type", "")

    if event_type == "map_image" and not _saved_map:
        b64 = meta.get("image_b64", "")
        if b64:
            path = _save_image("map.png", b64)
            if path:
                robots = meta.get("robots_on_map", 0)
                _flush_stream()
                _out(f"  {_color('[IMG   ]', _MAGENTA)} Карта сохранена: {path}  ({robots} роботов)")
                _saved_map = True

    elif event_type == "route_images":
        images = meta.get("images") or []
        winner = meta.get("winner", "")
        for img in images:
            name = img.get("name", "route")
            if name in _saved_routes:
                continue
            b64 = img.get("image_b64", "")
            if not b64:
                continue
            is_best = img.get("is_best", False) or name == winner
            filename = f"route_{name}{'_BEST' if is_best else ''}.png"
            path = _save_image(filename, b64)
            if path:
                tag = _color("★ лучший", _GREEN) if is_best else ""
                _flush_stream()
                _out(f"  {_color('[IMG   ]', _MAGENTA)} Маршрут {_color(name, _BOLD)}: {path} {tag}")
                _saved_routes.add(name)


# ─── event renderer ───────────────────────────────────────────────────────────

def _render_event(ev: dict) -> None:
    """Print a single event in a readable live format."""
    _handle_image_events(ev)

    source = ev.get("source", "")
    msg = ev.get("message", "")
    meta = ev.get("meta") or {}
    level = ev.get("level", "info")

    label_color = _SOURCE_COLORS.get(source, _DIM)
    label = _SOURCE_LABELS.get(source, source.upper()[:6])
    prefix = _color(f"[{label:<6}]", label_color)

    if level == "error":
        msg = _color(msg, _RED)
    elif level == "warning":
        msg = _color(msg, _YELLOW)

    event_type = meta.get("event_type", "")

    # ── Step/task lifecycle events ──────────────────────────────────────────
    if "step" in event_type and "start" in event_type:
        _flush_stream()
        agent = meta.get("agent", "")
        step_id = meta.get("step_id", "")
        _out(f"\n  {prefix} {_color(f'► Step {step_id} — {agent}', _BOLD + _CYAN)}")
        return
    if "step" in event_type and "complet" in event_type:
        _flush_stream()
        agent = meta.get("agent", "")
        step_id = meta.get("step_id", "")
        _out(f"  {prefix} {_color(f'✓ Step {step_id} — {agent} завершён', _GREEN)}")
        return
    if "task_complet" in event_type or msg == "Task completed":
        _flush_stream()
        _out(f"\n  {_color('✓ ЗАДАЧА ЗАВЕРШЕНА', _BOLD + _GREEN)}")
        return
    if "task_fail" in event_type or msg == "Task failed":
        _flush_stream()
        _out(f"\n  {_color('✗ ЗАДАЧА ПРОВАЛЕНА', _BOLD + _RED)}")
        return

    # ── Handoff / retry ─────────────────────────────────────────────────────
    if "Handoff to" in msg:
        _flush_stream()
        _out(f"  {prefix} {_color(msg, _CYAN)}")
        return
    if "Повтор шага" in msg:
        _flush_stream()
        _out(f"  {prefix} {_color(msg, _YELLOW)}")
        return

    # ── Streaming text delta (raw_response_event) ────────────────────────────
    sdk_event = meta.get("sdk_event", "")
    if sdk_event == "raw_response_event":
        agent_name = meta.get("agent", "?")
        if _streaming_active["agent"] != agent_name:
            _flush_stream()
            indent = f"  {prefix} "
            print(indent, end="", flush=True)
            _log(indent)
            _streaming_active["agent"] = agent_name
        print(msg, end="", flush=True)
        _log(msg)
        return

    # ── All other SDK events ─────────────────────────────────────────────────
    _flush_stream()
    if not msg or msg in {"Task accepted", "Plan created"}:
        return
    if sdk_event == "message_output_created":
        return
    # Skip image events — already handled above
    if meta.get("type") in {"map_image", "route_images"}:
        return

    # Long multi-line messages — indent each line
    if source in _AGENT_SOURCES and len(msg) > 80:
        _out(f"  {prefix}")
        for line in msg.splitlines():
            _out(f"           {line}")
        return

    _out(f"  {prefix} {msg}")


# ─── steps ────────────────────────────────────────────────────────────────────

def create_and_run(host: str, prompt: str) -> str:
    _section("1. Создание и запуск задачи")
    resp = _req("POST", f"{host}/task", {"prompt": prompt})
    task_id = resp["task_id"]
    _out(f"  task_id = {_color(task_id, _BOLD)}")
    _out(f"  status  = {resp.get('status', '?')}")
    return task_id


def stream_until_done(host: str, task_id: str, timeout: int = 300) -> str:
    """Poll /events incrementally and render agent output live."""
    _section("2. Живой вывод агентов")

    terminal = {"completed", "failed", "canceled"}
    deadline = time.time() + timeout
    after_seq = 0
    status = "running"
    poll_interval = 0.5

    while time.time() < deadline:
        resp = _req("GET", f"{host}/task/{task_id}/events?after_seq={after_seq}")
        events = resp.get("events") or []

        for ev in events:
            _render_event(ev)
        after_seq = resp.get("last_seq", after_seq)

        status_resp = _req("GET", f"{host}/task/{task_id}/status")
        status = status_resp["task"]["status"]

        if status in terminal:
            resp = _req("GET", f"{host}/task/{task_id}/events?after_seq={after_seq}")
            for ev in (resp.get("events") or []):
                _render_event(ev)
            break

        time.sleep(poll_interval)
    else:
        _flush_stream()
        _out(f"\n  {_color(f'✗ Таймаут {timeout}с — последний статус: {status}', _RED)}")

    _flush_stream()
    return status


def show_plan(host: str, task_id: str) -> None:
    _section("3. Итоговый план")
    resp = _req("GET", f"{host}/task/{task_id}/plan")
    plan = resp.get("plan") or []
    if not plan:
        _out("  (план пуст)")
        return
    for step in plan:
        st = step.get("status", "pending")
        icon = _STEP_ICONS.get(st, "·")
        icon_color = _GREEN if st == "completed" else _RED if st == "failed" else _DIM
        agent = step.get("agent", "?")
        desc = step.get("description", "")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        _out(
            f"  {_color(icon, icon_color)} [{step['id']}] "
            f"{_color(agent, _BOLD):<28} "
            f"{_color(st, icon_color):<12}  "
            f"{_color(desc, _DIM)}"
        )
    _out("")


def show_logs(host: str, task_id: str) -> None:
    _section("4. Логи")
    resp = _req("GET", f"{host}/task/{task_id}/logs")
    logs = resp.get("logs") or []
    if not logs:
        _out("  (логов нет)")
        return
    for i, entry in enumerate(logs, 1):
        _out(f"  {_color(str(i).rjust(3), _DIM)}. {entry}")


def show_artifacts() -> None:
    if not _artifact_dir:
        return
    files = sorted(_artifact_dir.iterdir())
    if not files:
        return
    _section("5. Артефакты")
    for f in files:
        size = f.stat().st_size
        size_str = f"{size // 1024} KB" if size >= 1024 else f"{size} B"
        _out(f"  {_color(f.name, _BOLD):<40} {_color(size_str, _DIM)}")
    _out(f"\n  Папка: {_color(str(_artifact_dir.resolve()), _CYAN)}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    global _log_file, _saved_map, _saved_routes

    parser = argparse.ArgumentParser(description="Orchestrator task lifecycle demo")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Base URL of orchestrator")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Task prompt")
    parser.add_argument("--timeout", type=int, default=300, help="Wait timeout in seconds")
    parser.add_argument(
        "--log",
        metavar="FILE",
        help="Write output to FILE (pass 'auto' to auto-name). "
             "Deprecated: artifacts are always saved to logs/<task_id>/",
    )
    args = parser.parse_args()

    host = args.host.rstrip("/")

    # Legacy --log flag: if pointing to a file, use it; otherwise ignored (artifacts go to logs/<id>/)
    legacy_log: Path | None = None
    if args.log and args.log != "auto":
        legacy_log = Path(args.log)

    _out(f"\n{_color('Оркестратор:', _BOLD)} {host}")
    _out(f"{_color('Промпт:     ', _BOLD)} {args.prompt}")

    # Create task first to get task_id
    task_id = create_and_run(host, args.prompt)

    # Init artifact directory now that we have task_id
    artifact_dir = _init_artifact_dir(task_id)
    _log_file = artifact_dir / "run.log"
    _log_file.write_text(
        f"# Orchestrator run — {datetime.now(timezone.utc).isoformat()}\n"
        f"# host:   {host}\n"
        f"# prompt: {args.prompt}\n"
        f"# task:   {task_id}\n\n",
        encoding="utf-8",
    )
    _out(f"  {_color(f'Артефакты: {artifact_dir.resolve()}', _DIM)}")

    # Reset image tracking state for this run
    _saved_map = False
    _saved_routes.clear()

    final_status = stream_until_done(host, task_id, timeout=args.timeout)
    show_plan(host, task_id)
    show_logs(host, task_id)
    show_artifacts()

    color = _GREEN if final_status == "completed" else _RED
    _out(f"\n{_color('─' * 60, _DIM)}")
    _out(f"  Статус:  {_color(final_status.upper(), _BOLD + color)}")
    _out(f"  task_id: {task_id}")
    _out(f"  Swagger: {host}/docs")
    _out(f"{_color('─' * 60, _DIM)}\n")

    # Save raw events and plan to artifact dir
    all_events = _req("GET", f"{host}/task/{task_id}/events?after_seq=0")
    raw_plan = _req("GET", f"{host}/task/{task_id}/plan")
    raw_logs = _req("GET", f"{host}/task/{task_id}/logs")

    (artifact_dir / "events.json").write_text(
        json.dumps(all_events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifact_dir / "plan.json").write_text(
        json.dumps(raw_plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifact_dir / "task_logs.json").write_text(
        json.dumps(raw_logs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  {_color(f'Сохранено в: {artifact_dir.resolve()}', _GREEN)}")

    # Legacy --log support
    if legacy_log:
        import shutil
        shutil.copy(artifact_dir / "run.log", legacy_log)
        print(f"  {_color(f'Лог: {legacy_log.resolve()}', _DIM)}")


if __name__ == "__main__":
    main()
