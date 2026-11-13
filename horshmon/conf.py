from __future__ import annotations

import copy
from pathlib import Path

import yaml

DEFAULTS = {
    "interval": 60,
    "timeout": 10,
    "ssl_warn_days": 14,
    "telegram": {"token": "", "chat_id": ""},
    "local": {"disk": 90, "ram": 90, "cpu": 90},
    "targets": [],
}

EXAMPLE = """interval: 60
timeout: 10
ssl_warn_days: 14

telegram:
  token: ""
  chat_id: ""

local:
  disk: 90
  ram: 90
  cpu: 90

targets:
  - name: example
    url: https://example.com
    keyword: Example Domain
  - name: google-dns
    host: 8.8.8.8
    port: 53
"""


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path} (run 'horshmon init')")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"invalid config: {path}")
    cfg = copy.deepcopy(DEFAULTS)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(value)
        else:
            cfg[key] = value
    for target in cfg["targets"]:
        if "name" not in target:
            raise ValueError("every target needs a name")
        if "url" not in target and not ("host" in target and "port" in target):
            raise ValueError(f"target '{target['name']}' needs a url or a host/port pair")
    return cfg