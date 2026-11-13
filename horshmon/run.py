from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from horshmon import __author__, __version__
from horshmon.probes import Result, run_checks
from horshmon.conf import EXAMPLE, load_config
from horshmon.tg import format_events, send_telegram
from horshmon.store import load_state, save_state, transitions, update

console = Console()
BANNER = f"[bold]horshmon[/bold] {__version__} [dim]by {__author__}[/dim]"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="horshmon",
        description="Uptime, SSL certificate and server health monitor with Telegram alerts.",
        epilog=f"by {__author__}",
    )
    parser.add_argument("--version", action="version", version=f"horshmon {__version__} by {__author__}")
    parser.add_argument("-c", "--config", default="config.yml")
    parser.add_argument("-s", "--state", default="state.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create a starter config.yml")
    sub.add_parser("check", help="run all checks once and exit")
    watch = sub.add_parser("watch", help="run checks in a loop")
    watch.add_argument("-i", "--interval", type=int, default=None)
    sub.add_parser("status", help="show the last saved results")
    return parser


def print_results(results: list[Result]) -> None:
    table = Table(title=f"horshmon by {__author__}")
    table.add_column("target", style="bold")
    table.add_column("kind")
    table.add_column("status")
    table.add_column("detail")
    for result in results:
        if not result.ok:
            status = "[red]DOWN[/red]"
        elif result.warn:
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[green]OK[/green]"
        table.add_row(result.name, result.kind, status, result.detail)
    console.print(table)


def run_once(cfg: dict, state_path: Path) -> int:
    results = run_checks(cfg)
    print_results(results)
    state = load_state(state_path)
    events = transitions(state, results)
    if events:
        text = format_events(events)
        if send_telegram(cfg, text):
            console.print("[dim]telegram alert sent[/dim]")
        else:
            console.print(text)
    save_state(state_path, update(state, results))
    return 0 if all(result.ok for result in results) else 1


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.config)
    if path.exists():
        console.print(f"[yellow]{path} already exists[/yellow]")
        return 1
    path.write_text(EXAMPLE, encoding="utf-8")
    console.print(f"created [bold]{path}[/bold]")
    return 0


def cmd_watch(args: argparse.Namespace, cfg: dict, state_path: Path) -> int:
    interval = args.interval or cfg["interval"]
    console.print(f"[dim]watching every {interval}s, ctrl+c to stop[/dim]")
    try:
        while True:
            run_once(cfg, state_path)
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("[dim]stopped[/dim]")
        return 0


def cmd_status(state_path: Path) -> int:
    state = load_state(state_path)
    if not state.get("checks"):
        console.print("no results yet, run 'horshmon check' first")
        return 1
    table = Table(title=f"last results - horshmon by {__author__}")
    table.add_column("target", style="bold")
    table.add_column("kind")
    table.add_column("status")
    table.add_column("detail")
    for name, saved in state["checks"].items():
        target, _, kind = name.partition(":")
        if not saved["ok"]:
            status = "[red]DOWN[/red]"
        elif saved.get("warn"):
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[green]OK[/green]"
        table.add_row(target, kind, status, saved["detail"])
    console.print(table)
    return 0


def main() -> None:
    args = build_parser().parse_args()
    console.print(BANNER)
    if args.command == "init":
        sys.exit(cmd_init(args))
    try:
        cfg = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        sys.exit(2)
    state_path = Path(args.state)
    if args.command == "check":
        sys.exit(run_once(cfg, state_path))
    if args.command == "watch":
        sys.exit(cmd_watch(args, cfg, state_path))
    if args.command == "status":
        sys.exit(cmd_status(state_path))


if __name__ == "__main__":
    main()