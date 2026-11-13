from __future__ import annotations

import os
import socket
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import psutil
import requests

from horshmon import __author__, __version__

USER_AGENT = f"horshmon/{__version__} (by {__author__})"


@dataclass
class Result:
    name: str
    kind: str
    ok: bool
    detail: str
    warn: bool = False


def _reason(exc: Exception) -> str:
    if isinstance(exc, requests.exceptions.Timeout):
        return "timed out"
    root = exc
    seen = set()
    while id(root) not in seen:
        seen.add(id(root))
        nxt = root.__cause__ or root.__context__
        if nxt is None:
            break
        root = nxt
    if isinstance(root, ConnectionRefusedError):
        return "connection refused"
    if isinstance(root, socket.gaierror):
        return "dns lookup failed"
    if isinstance(root, (socket.timeout, TimeoutError)):
        return "timed out"
    if isinstance(root, ssl.SSLError):
        return "ssl: " + (root.reason or "error").replace("_", " ").lower()
    if isinstance(root, OSError):
        return (root.strerror or root.__class__.__name__).lower()
    text = str(root).strip()
    return text.splitlines()[0][:120] if text else root.__class__.__name__


def http_check(target: dict, timeout: float) -> Result:
    name = target["name"]
    expect = target.get("expect")
    keyword = target.get("keyword")
    start = time.monotonic()
    try:
        resp = requests.get(
            target["url"],
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        ms = (time.monotonic() - start) * 1000
        if expect is not None and resp.status_code != expect:
            return Result(name, "http", False, f"status {resp.status_code}, expected {expect}")
        if expect is None and resp.status_code >= 400:
            return Result(name, "http", False, f"status {resp.status_code}")
        if keyword and keyword not in resp.text:
            return Result(name, "http", False, f"keyword '{keyword}' not found")
        return Result(name, "http", True, f"{resp.status_code} in {ms:.0f} ms")
    except requests.RequestException as exc:
        return Result(name, "http", False, _reason(exc))


def ssl_check(name: str, host: str, port: int, timeout: float, warn_days: int) -> Result:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
        expires = ssl.cert_time_to_seconds(cert["notAfter"])
        days = (expires - time.time()) / 86400
        if days < 0:
            return Result(name, "ssl", False, f"certificate expired {-days:.0f} days ago")
        if days <= warn_days:
            return Result(name, "ssl", True, f"expires in {days:.0f} days", warn=True)
        return Result(name, "ssl", True, f"expires in {days:.0f} days")
    except (OSError, KeyError, ValueError) as exc:
        return Result(name, "ssl", False, _reason(exc))


def tcp_check(name: str, host: str, port: int, timeout: float) -> Result:
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            ms = (time.monotonic() - start) * 1000
        return Result(name, "tcp", True, f"port {port} open in {ms:.0f} ms")
    except OSError as exc:
        return Result(name, "tcp", False, _reason(exc))


def local_checks(limits: dict) -> list[Result]:
    results = []
    if limits.get("disk"):
        pct = psutil.disk_usage(os.path.abspath(os.sep)).percent
        results.append(Result("local", "disk", pct < limits["disk"], f"{pct:.0f}% used"))
    if limits.get("ram"):
        pct = psutil.virtual_memory().percent
        results.append(Result("local", "ram", pct < limits["ram"], f"{pct:.0f}% used"))
    if limits.get("cpu"):
        pct = psutil.cpu_percent(interval=0.5)
        results.append(Result("local", "cpu", pct < limits["cpu"], f"{pct:.0f}% used"))
    return results


def run_checks(cfg: dict) -> list[Result]:
    results = []
    timeout = cfg["timeout"]
    for target in cfg["targets"]:
        if "url" in target:
            results.append(http_check(target, timeout))
            if target["url"].startswith("https://"):
                parsed = urlparse(target["url"])
                results.append(
                    ssl_check(target["name"], parsed.hostname, parsed.port or 443, timeout, cfg["ssl_warn_days"])
                )
        else:
            port = int(target["port"])
            results.append(tcp_check(target["name"], target["host"], port, timeout))
            if target.get("ssl"):
                results.append(ssl_check(target["name"], target["host"], port, timeout, cfg["ssl_warn_days"]))
    results.extend(local_checks(cfg["local"]))
    return results