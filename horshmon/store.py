from __future__ import annotations

import json
from pathlib import Path

from horshmon import __author__, __version__
from horshmon.probes import Result

GENERATOR = f"horshmon {__version__} by {__author__}"


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"generator": GENERATOR, "checks": {}}


def save_state(path: Path, state: dict) -> None:
    state["generator"] = GENERATOR
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def key(result: Result) -> str:
    return f"{result.name}:{result.kind}"


def transitions(previous: dict, results: list[Result]) -> list[dict]:
    events = []
    checks = previous.get("checks", {})
    for result in results:
        was = checks.get(key(result))
        if was is None:
            if not result.ok:
                events.append({"type": "down", "result": result})
            elif result.warn:
                events.append({"type": "warn", "result": result})
            continue
        if was["ok"] and not result.ok:
            events.append({"type": "down", "result": result})
        elif not was["ok"] and result.ok:
            events.append({"type": "up", "result": result})
        elif result.ok and result.warn and not was.get("warn"):
            events.append({"type": "warn", "result": result})
    return events


def update(previous: dict, results: list[Result]) -> dict:
    previous["checks"] = {
        key(result): {"ok": result.ok, "warn": result.warn, "detail": result.detail}
        for result in results
    }
    return previous