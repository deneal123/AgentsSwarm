"""
Пример полного цикла работы с задачей оркестратора.
Показывает живой вывод агентов в реальном времени во время выполнения.

Запуск:
    python examples/task_lifecycle.py
    python examples/task_lifecycle.py --host http://185.55.57.82:8009
    python examples/task_lifecycle.py --prompt "Покажи статус carter01"
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

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
    print(f"\n{_color('─' * 60, _DIM)}")
    print(f"  {_color(title, _BOLD)}")
    print(f"{_color('─' * 60, _DIM)}")


def _pretty(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _render_event(ev: dict) -> None:
    """Print a single event in a readable live format."""
    source = ev.get("source", "")
    msg = ev.get("message", "")
    meta = ev.get("meta") or {}
    level = ev.get("level", "info")

    label_color = _SOURCE_COLORS.get(source, _DIM)
    label = _SOURCE_LABELS.get(source, source.upper()[:6])

    # Prefix: colored [LABEL]
    prefix = _color(f"[{label:<6}]", label_color)

    # Highlight errors/warnings
    if level == "error":
        msg = _color(msg, _RED)
    elif level == "warning":
        msg = _color(msg, _YELLOW)

    # Show step transitions more prominently
    event_type = meta.get("event_type", "")
    if "step" in event_type and "start" in event_type:
        agent = meta.get("agent", "")
        step_id = meta.get("step_id", "")
        print(f"\n  {prefix} {_color(f'► Step {step_id} — {agent}', _BOLD + _CYAN)}")
        return
    if "step" in event_type and "complet" in event_type:
        agent = meta.get("agent", "")
        step_id = meta.get("step_id", "")
        print(f"  {prefix} {_color(f'✓ Step {step_id} — {agent} завершён', _GREEN)}")
        return
    if "task_complet" in event_type or msg == "Task completed":
        print(f"\n  {_color('✓ ЗАДАЧА ЗАВЕРШЕНА', _BOLD + _GREEN)}")
        return
    if "task_fail" in event_type or msg == "Task failed":
        print(f"\n  {_color('✗ ЗАДАЧА ПРОВАЛЕНА', _BOLD + _RED)}")
        return

    # Show handoff info distinctly
    if "Handoff to" in msg:
        print(f"  {prefix} {_color(msg, _CYAN)}")
        return

    # Show retry distinctly
    if "Повтор шага" in msg:
        print(f"  {prefix} {_color(msg, _YELLOW)}")
        return

    # Long agent messages (actual output) — show with indent
    if source in _AGENT_SOURCES and len(msg) > 80:
        print(f"  {prefix}")
        for line in msg.splitlines():
            print(f"           {line}")
        return

    # Default: single line
    if msg and msg not in {"Task accepted", "Plan created"}:
        print(f"  {prefix} {msg}")


# ─── steps ────────────────────────────────────────────────────────────────────

def create_and_run(host: str, prompt: str) -> str:
    _section("1. Создание и запуск задачи")
    resp = _req("POST", f"{host}/task", {"prompt": prompt})
    task_id = resp["task_id"]
    print(f"  task_id = {_color(task_id, _BOLD)}")
    print(f"  status  = {resp.get('status', '?')}")
    return task_id


def stream_until_done(host: str, task_id: str, timeout: int = 120) -> str:
    """Poll /events incrementally and render agent output live."""
    _section("2. Живой вывод агентов")

    terminal = {"completed", "failed", "canceled"}
    deadline = time.time() + timeout
    after_seq = 0
    status = "running"
    poll_interval = 0.5

    while time.time() < deadline:
        # Fetch new events since last seq
        resp = _req("GET", f"{host}/task/{task_id}/events?after_seq={after_seq}")
        events = resp.get("events") or []

        for ev in events:
            _render_event(ev)
            after_seq = max(after_seq, ev.get("seq", after_seq))

        # Check task status
        status_resp = _req("GET", f"{host}/task/{task_id}/status")
        status = status_resp["task"]["status"]

        if status in terminal:
            # Drain any remaining events one more time
            resp = _req("GET", f"{host}/task/{task_id}/events?after_seq={after_seq}")
            for ev in (resp.get("events") or []):
                _render_event(ev)
            break

        time.sleep(poll_interval)
    else:
        print(f"\n  {_color(f'✗ Таймаут {timeout}с — последний статус: {status}', _RED)}")

    return status


def show_plan(host: str, task_id: str) -> None:
    _section("3. Итоговый план")
    resp = _req("GET", f"{host}/task/{task_id}/plan")
    plan = resp.get("plan") or []
    if not plan:
        print("  (план пуст)")
        return
    for step in plan:
        st = step.get("status", "pending")
        icon = _STEP_ICONS.get(st, "·")
        icon_color = _GREEN if st == "completed" else _RED if st == "failed" else _DIM
        agent = step.get("agent", "?")
        desc = step.get("description", "")
        # Truncate long descriptions (map context etc.)
        if len(desc) > 80:
            desc = desc[:77] + "..."
        print(
            f"  {_color(icon, icon_color)} [{step['id']}] "
            f"{_color(agent, _BOLD):<28} "
            f"{_color(st, icon_color):<12}  "
            f"{_color(desc, _DIM)}"
        )
    print()


def show_logs(host: str, task_id: str) -> None:
    _section("4. Логи")
    resp = _req("GET", f"{host}/task/{task_id}/logs")
    logs = resp.get("logs") or []
    if not logs:
        print("  (логов нет)")
        return
    for i, entry in enumerate(logs, 1):
        print(f"  {_color(str(i).rjust(3), _DIM)}. {entry}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrator task lifecycle demo")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Base URL of orchestrator")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Task prompt")
    parser.add_argument("--timeout", type=int, default=120, help="Wait timeout in seconds")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    print(f"\n{_color('Оркестратор:', _BOLD)} {host}")
    print(f"{_color('Промпт:     ', _BOLD)} {args.prompt}")

    task_id = create_and_run(host, args.prompt)
    final_status = stream_until_done(host, task_id, timeout=args.timeout)
    show_plan(host, task_id)
    show_logs(host, task_id)

    color = _GREEN if final_status == "completed" else _RED
    print(f"\n{_color('─' * 60, _DIM)}")
    print(f"  Статус:  {_color(final_status.upper(), _BOLD + color)}")
    print(f"  task_id: {task_id}")
    print(f"  Swagger: {host}/docs")
    print(f"{_color('─' * 60, _DIM)}\n")


if __name__ == "__main__":
    main()
