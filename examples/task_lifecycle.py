"""
Пример полного цикла работы с задачей оркестратора.

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
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _pretty(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ─── steps ────────────────────────────────────────────────────────────────────

def create_and_run(host: str, prompt: str) -> str:
    _section("1. Создание и запуск задачи")
    resp = _req("POST", f"{host}/task", {"prompt": prompt})
    _pretty(resp)
    task_id = resp["task_id"]
    print(f"\n  ✓ task_id = {task_id}")
    return task_id


def wait_for_terminal(host: str, task_id: str, timeout: int = 60) -> str:
    _section("2. Статус задачи (ожидание завершения)")
    terminal = {"completed", "failed", "canceled"}
    deadline = time.time() + timeout
    status = "unknown"

    while time.time() < deadline:
        resp = _req("GET", f"{host}/task/{task_id}/status")
        status = resp["task"]["status"]
        plan = resp["task"].get("plan") or []
        done = sum(1 for s in plan if s.get("status") in terminal)
        total = len(plan)
        print(f"  status={status}  steps={done}/{total}", end="\r", flush=True)

        if status in terminal:
            print()
            _pretty(resp)
            break
        time.sleep(1)
    else:
        print(f"\n  ✗ Таймаут {timeout}с — последний статус: {status}")

    return status


def show_plan(host: str, task_id: str) -> None:
    _section("3. План задачи")
    resp = _req("GET", f"{host}/task/{task_id}/plan")
    plan = resp.get("plan") or []
    if not plan:
        print("  (план пуст)")
        return
    for step in plan:
        icon = {"completed": "✓", "failed": "✗", "canceled": "⊘", "running": "►"}.get(
            step.get("status", ""), "·"
        )
        agent = step.get("agent", "?")
        desc = step.get("description", "")
        status = step.get("status", "pending")
        print(f"  {icon} [{step['id']}] {agent:20s} {status:10s}  {desc}")
    print()
    _pretty(resp)


def show_logs(host: str, task_id: str) -> None:
    _section("4. Логи задачи")
    resp = _req("GET", f"{host}/task/{task_id}/logs")
    logs = resp.get("logs") or []
    if not logs:
        print("  (логов нет)")
        return
    for i, entry in enumerate(logs, 1):
        # logs are strings: "[level] source: message"
        print(f"  {i:>3}. {entry}")


def show_events(host: str, task_id: str) -> None:
    _section("5. Потоковые события задачи")
    resp = _req("GET", f"{host}/task/{task_id}/events")
    events = resp.get("events") or []
    total = resp.get("total", len(events))
    print(f"  Всего событий: {total}\n")
    for ev in events:
        seq = ev.get("seq", "?")
        ts = ev.get("ts", "")[:19]
        level = ev.get("level", "info").upper()[:5]
        source = ev.get("source", "")
        msg = ev.get("message", "")
        meta = ev.get("meta") or {}
        meta_str = f"  meta={json.dumps(meta, ensure_ascii=False)}" if meta else ""
        print(f"  [{seq:>3}] {ts}  {level:5s}  [{source}]  {msg}{meta_str}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Orchestrator task lifecycle demo")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Base URL of orchestrator")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Task prompt")
    parser.add_argument("--timeout", type=int, default=60, help="Wait timeout in seconds")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    print(f"\nОркестратор: {host}")
    print(f"Промпт:      {args.prompt}")

    task_id = create_and_run(host, args.prompt)
    wait_for_terminal(host, task_id, timeout=args.timeout)
    show_plan(host, task_id)
    show_logs(host, task_id)
    show_events(host, task_id)

    print(f"\n{'─' * 60}")
    print(f"  Готово. task_id = {task_id}")
    print(f"  Swagger: {host}/docs")
    print(f"{'─' * 60}\n")


if __name__ == "__main__":
    main()
