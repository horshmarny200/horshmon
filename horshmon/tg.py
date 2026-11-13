from __future__ import annotations

import requests

from horshmon import __author__, __version__

SIGNATURE = f"horshmon {__version__} by {__author__}"
HEADERS = {"User-Agent": f"horshmon/{__version__} (by {__author__})"}
LABELS = {"down": "DOWN", "up": "RECOVERED", "warn": "WARNING"}


def format_events(events: list[dict]) -> str:
    lines = []
    for event in events:
        result = event["result"]
        lines.append(f"[{LABELS[event['type']]}] {result.name} ({result.kind})")
        lines.append(result.detail)
        lines.append("")
    lines.append(f"-- {SIGNATURE}")
    return "\n".join(lines).strip()


def send_telegram(cfg: dict, text: str) -> bool:
    token = cfg["telegram"].get("token", "")
    chat_id = cfg["telegram"].get("chat_id", "")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            headers=HEADERS,
            timeout=15,
        )
        return resp.ok
    except requests.RequestException:
        return False