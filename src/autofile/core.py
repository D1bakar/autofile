"""Core: classify loose files, build a move plan, execute it safely.

Safety model
------------
* Only *top-level loose files* in the watch root are considered. Directories
  (i.e. projects) are never entered and never moved.
* The tool's own folders and anything in ``ignore_names`` are skipped.
* The default mode builds a plan and changes nothing; ``execute`` only runs
  for moves the caller explicitly approved.
* Name conflicts are resolved by renaming the destination, never by
  overwriting.
* Every accepted move is appended to a log file.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

OTHER = "other"


@dataclass(frozen=True)
class Move:
    src: Path
    dst: Path
    category: str


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    if "rules" not in config:
        raise ValueError(f"config {path} has no 'rules' section")
    return config


def build_ext_index(rules: dict[str, list[str]]) -> dict[str, str]:
    """Flatten {category: [exts]} into {ext: category}. Last rule wins."""
    index: dict[str, str] = {}
    for category, exts in rules.items():
        for ext in exts:
            index[ext.lower()] = category
    return index


def classify(filename: str, ext_index: dict[str, str]) -> str:
    ext = Path(filename).suffix.lower()
    return ext_index.get(ext, OTHER)


def scan(root: Path, ext_index: dict[str, str], ignore_names: set[str]) -> list[Path]:
    """Return loose top-level files worth considering.

    Skips directories, hidden files, and ignored names (case-insensitive).
    """
    found: list[Path] = []
    ignored = {n.lower() for n in ignore_names}
    for entry in sorted(root.iterdir()):
        name = entry.name
        if name.startswith("."):
            continue
        if name.lower() in ignored:
            continue
        if not entry.is_file():
            continue  # projects and bins: never touched
        found.append(entry)
    return found


def conflict_free(dst: Path) -> Path:
    """Return dst, or 'name (2).ext', 'name (3).ext'… if it already exists."""
    if not dst.exists():
        return dst
    stem, suffix, parent = dst.stem, dst.suffix, dst.parent
    n = 2
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def plan(files: list[Path], root: Path, out_dir: str, ext_index: dict[str, str]) -> list[Move]:
    moves: list[Move] = []
    for src in files:
        category = classify(src.name, ext_index)
        dst = root / out_dir / category / src.name
        moves.append(Move(src=src, dst=dst, category=category))
    return moves


def setup_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("autofile")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s"))
    logger.addHandler(handler)
    return logger


def execute(moves: list[Move], log_path: Path, approve) -> tuple[int, int]:
    """Run approved moves. ``approve(Move) -> bool`` decides per file.

    Returns (moved, skipped). Destination conflicts are renamed, never
    overwritten. Each executed move is logged.
    """
    logger = setup_logging(log_path)
    moved = skipped = 0
    for move in moves:
        if not approve(move):
            skipped += 1
            logger.info("SKIP  %s (user declined)", move.src.name)
            continue
        final_dst = conflict_free(move.dst)
        final_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(move.src), str(final_dst))
        moved += 1
        if final_dst != move.dst:
            logger.info("MOVE  %s -> %s (renamed, target existed)", move.src.name, final_dst)
        else:
            logger.info("MOVE  %s -> %s", move.src.name, final_dst)
    return moved, skipped
