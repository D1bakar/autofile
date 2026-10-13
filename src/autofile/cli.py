"""Command-line interface for autofile.

Default mode is a dry run: it prints the plan and changes nothing.
``--apply`` executes the plan after per-file confirmation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import core


def build_plan(config_path: Path) -> tuple[dict, list[core.Move], Path]:
    config = core.load_config(config_path)
    root = Path(config["watch_path"]).expanduser()
    out_dir = config.get("output_dir", "_sorted")
    ignore = set(config.get("ignore_names", [])) | {out_dir}
    ext_index = core.build_ext_index(config["rules"])
    files = core.scan(root, ext_index, ignore)
    return config, core.plan(files, root, out_dir, ext_index), root


def print_plan(moves: list[core.Move], root: Path) -> None:
    if not moves:
        print(f"nothing to sort in {root} — already tidy.")
        return
    print(f"plan for {root}  ({len(moves)} loose file(s))\n")
    width = max(len(m.category) for m in moves)
    for m in moves:
        rel_src = m.src.relative_to(root)
        rel_dst = m.dst.relative_to(root)
        print(f"  {m.category:<{width}}  {rel_src}  ->  {rel_dst}")
    print("\n(dry run - nothing was moved. use --apply to execute.)")


class Prompter:
    """Per-file y/n/all/quit approval state."""

    def __init__(self) -> None:
        self._all: bool | None = None

    def approve(self, move: core.Move) -> bool:
        if self._all is not None:
            return self._all
        try:
            answer = input(f"  move {move.src.name} -> {move.dst.parent.name}/{move.dst.name}? [y/n/a/q] ").strip().lower()
        except EOFError:
            return False
        if answer == "a":
            self._all = True
            return True
        if answer == "q":
            self._all = False
            return False
        return answer in ("y", "yes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="autofile", description="Sort loose files by type. Dry-run by default.")
    parser.add_argument("--config", type=Path, default=Path("config.json"), help="path to config.json")
    parser.add_argument("--apply", action="store_true", help="execute the plan after confirmation (default: dry run)")
    parser.add_argument("--watch", action="store_true", help="watch the folder and sort new files as they land")
    parser.add_argument("--yes", action="store_true", help="auto-approve moves without prompting (use with care)")
    parser.add_argument("--duration", type=float, default=0, help="stop watching after N seconds (mainly for testing)")
    args = parser.parse_args(argv)

    try:
        config, moves, root = build_plan(args.config)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.watch:
        try:
            from .watcher import run_watcher  # lazy: watchdog is optional
        except ImportError:
            print("watch mode needs watchdog: pip install watchdog", file=sys.stderr)
            return 1
        return run_watcher(args.config, duration=args.duration, auto_yes=args.yes)

    if not args.apply:
        print_plan(moves, root)
        return 0

    if not moves:
        print("nothing to do.")
        return 0

    print_plan(moves, root)
    print()
    log_path = Path(args.config).resolve().parent / "autofile.log"
    approve = (lambda m: True) if args.yes else Prompter().approve
    try:
        moved, skipped = core.execute(moves, log_path, approve)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"\ndone: {moved} moved, {skipped} skipped. log: {log_path}")
    return 0
