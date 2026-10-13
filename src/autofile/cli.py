"""Command-line interface for autofile.

Run it with no arguments and you get a friendly numbered menu — no flags to
remember, plain English, safe by default (nothing moves until you pick 2 or 3).

The flags (--apply, --watch, --yes…) still exist for scripting and powers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import core

BANNER = """
------------------------------------------------------------
  AUTOFILE  -  sorts loose files into folders by type
------------------------------------------------------------"""


def build_plan(config_path: Path) -> tuple[dict, list[core.Move], Path]:
    config = core.load_config(config_path)
    root = Path(config["watch_path"]).expanduser()
    out_dir = config.get("output_dir", "_sorted")
    ignore = set(config.get("ignore_names", [])) | {out_dir}
    ext_index = core.build_ext_index(config["rules"])
    files = core.scan(root, ext_index, ignore)
    return config, core.plan(files, root, out_dir, ext_index), root


def friendly_plan(moves: list[core.Move], root: Path) -> None:
    if not moves:
        print(f"\n  All tidy! No loose files in '{root.name}'.\n")
        return
    print(f"\n  I would move {len(moves)} file(s) into folders by type:\n")
    width = max(len(m.src.name) for m in moves)
    for m in moves:
        print(f"    {m.src.name:<{width}}   ->  {m.category} folder")
    print("\n  Nothing has moved yet.\n")


def execute_moves(moves: list[core.Move], config_path: Path, auto_yes: bool) -> int:
    if not moves:
        print("\n  Nothing to sort - already tidy.\n")
        return 0
    log_path = config_path.resolve().parent / "autofile.log"
    approve = (lambda m: True) if auto_yes else Prompter().approve
    try:
        moved, skipped = core.execute(moves, log_path, approve)
    except OSError as exc:
        print(f"\n  Sorry, that failed: {exc}\n", file=sys.stderr)
        return 1
    print(f"\n  Done! {moved} file(s) sorted, {skipped} left alone.")
    print(f"  Everything is logged in {log_path.name}.\n")
    return 0


class Prompter:
    """Plain-English per-file approval: Y / N / All / Quit, Enter means Yes."""

    def __init__(self) -> None:
        self._all: bool | None = None

    def approve(self, move: core.Move) -> bool:
        if self._all is not None:
            return self._all
        folder = move.dst.parent.name
        while True:
            try:
                answer = input(
                    f'  Move "{move.src.name}" into the {folder} folder?  '
                    f"[Y]es / [N]o / [A]ll / [Q]uit  "
                ).strip().lower()
            except EOFError:
                return False
            if answer in ("", "y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            if answer in ("a", "all"):
                self._all = True
                return True
            if answer in ("q", "quit", "stop"):
                self._all = False
                return False
            print("    please type Y, N, A or Q")


def run_menu(config_path: Path) -> int:
    """The default experience: a numbered menu loop. No flags required."""
    while True:
        try:
            config, moves, root = build_plan(config_path)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print(BANNER)
        print(f"  folder : {root}")
        if moves:
            print(f"  found  : {len(moves)} loose file(s)")
        else:
            print("  found  : nothing - already tidy")
        print("           (project folders are never touched)")
        print()
        print("  1) Preview   - show what would happen (nothing moves)")
        print("  2) Sort all  - move every file now")
        print("  3) Review    - ask me about each file")
        print("  4) Watch     - sort new files as they land (Ctrl+C stops it)")
        print("  5) Quit")

        try:
            choice = input("\n  Your choice [1]: ").strip().lower() or "1"
        except EOFError:
            print("\n  Bye!")
            return 0

        if choice == "1":
            friendly_plan(moves, root)
        elif choice == "2":
            confirm = input(
                f"  Move all {len(moves)} file(s) now?  [Y]es / [N]o  "
            ).strip().lower()
            if confirm in ("", "y", "yes"):
                execute_moves(moves, config_path, auto_yes=True)
            else:
                print("\n  Okay, nothing was moved.\n")
        elif choice == "3":
            execute_moves(moves, config_path, auto_yes=False)
        elif choice == "4":
            try:
                from .watcher import run_watcher  # noqa: PLC0415
            except ImportError:
                print("\n  Watch mode needs one extra piece:")
                print("    pip install watchdog\n")
                continue
            run_watcher(config_path, auto_yes=False)  # Ctrl+C returns here
            print()
        elif choice in ("5", "q", "quit", "exit"):
            print("  Bye!")
            return 0
        else:
            print("\n  please type 1, 2, 3, 4 or 5\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autofile",
        description="Sort loose files by type. Just run it - it will ask you what to do.",
    )
    parser.add_argument("--config", type=Path, default=Path("config.json"), help="path to config.json")
    parser.add_argument("--apply", action="store_true", help="skip the menu: execute the plan with prompts")
    parser.add_argument("--watch", action="store_true", help="skip the menu: watch the folder")
    parser.add_argument("--yes", action="store_true", help="auto-approve moves without prompting (use with care)")
    parser.add_argument("--duration", type=float, default=0, help="stop watching after N seconds (mainly for testing)")
    args = parser.parse_args(argv)

    if args.watch:
        try:
            from .watcher import run_watcher  # noqa: PLC0415
        except ImportError:
            print("watch mode needs watchdog: pip install watchdog", file=sys.stderr)
            return 1
        return run_watcher(args.config, duration=args.duration, auto_yes=args.yes)

    if args.apply:
        try:
            _, moves, _ = build_plan(args.config)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return execute_moves(moves, args.config, auto_yes=args.yes)

    # no flags: the friendly menu
    try:
        return run_menu(args.config)
    except KeyboardInterrupt:
        print("\n  Bye!")
        return 0
