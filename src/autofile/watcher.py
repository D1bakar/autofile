"""Watch mode: react to new files as they land in the watch root.

Safety model (same as core, plus a settle window):
* Only files created directly in the watch root are considered — events from
  subdirectories (projects, the output bins) are ignored entirely.
* Each event is debounced and delayed by ``settle_seconds`` so half-finished
  downloads/copies are not sorted mid-write.
* Approval uses the same interactive prompt as --apply; declined files stay
  where they are and are logged as SKIP.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from . import core


def is_candidate(path: Path, root: Path, ignore_names: set[str]) -> bool:
    """True for loose top-level files we may sort. Never dirs, nested,
    hidden, or ignored names."""
    p = Path(path)
    if p.parent != root:
        return False
    if not p.is_file():
        return False
    if p.name.startswith("."):
        return False
    if p.name.lower() in {n.lower() for n in ignore_names}:
        return False
    return True


class SortHandler(FileSystemEventHandler):
    def __init__(
        self,
        root: Path,
        out_dir: str,
        ext_index: dict[str, str],
        ignore_names: set[str],
        settle_seconds: float,
        log_path: Path,
        approve,
    ) -> None:
        self.root = root
        self.out_dir = out_dir
        self.ext_index = ext_index
        self.ignore_names = ignore_names | {out_dir}
        self.settle_seconds = settle_seconds
        self.log_path = log_path
        self.approve = approve
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _queue(self, raw_path: str) -> None:
        p = Path(raw_path)
        if p.parent != self.root:
            return  # only the top level; projects and bins never trigger us
        key = str(p).lower()
        with self._lock:
            old = self._timers.pop(key, None)
            if old:
                old.cancel()
            timer = threading.Timer(self.settle_seconds, self._process, args=(p,))
            self._timers[key] = timer
            timer.start()

    def _process(self, p: Path) -> None:
        with self._lock:
            self._timers.pop(str(p).lower(), None)
        if not is_candidate(p, self.root, self.ignore_names):
            return
        move = core.plan([p], self.root, self.out_dir, self.ext_index)[0]
        rel = move.dst.relative_to(self.root)
        print(f"[watch] {p.name}  ->  {rel}", flush=True)
        try:
            core.execute([move], self.log_path, self.approve)
        except OSError as exc:
            # locked / half-written file: leave it, say so, keep watching
            print(f"[watch] skipped {p.name}: {exc}", flush=True)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        # files dragged INTO the root arrive as moves; watch the destination
        if not event.is_directory:
            self._queue(event.dest_path)


def run_watcher(config_path: Path, duration: float = 0, auto_yes: bool = False) -> int:
    from .cli import Prompter  # lazy: keeps import graph acyclic

    try:
        config = core.load_config(config_path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", flush=True)
        return 1

    root = Path(config["watch_path"]).expanduser()
    if not root.is_dir():
        print(f"error: watch_path does not exist: {root}", flush=True)
        return 1

    out_dir = config.get("output_dir", "_sorted")
    ext_index = core.build_ext_index(config["rules"])
    ignore = set(config.get("ignore_names", []))
    log_path = config_path.resolve().parent / "autofile.log"
    ignore.add(log_path.name)  # never try to sort our own open log
    settle = float(config.get("settle_seconds", 2))

    approve = (lambda m: True) if auto_yes else Prompter().approve
    handler = SortHandler(root, out_dir, ext_index, ignore, settle, log_path, approve)
    observer = Observer()
    observer.schedule(handler, str(root), recursive=False)
    observer.start()
    print(f"watching {root}  (settle {settle}s, ctrl+c to stop)", flush=True)

    try:
        if duration > 0:
            time.sleep(duration)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping...", flush=True)
    finally:
        observer.stop()
        observer.join(timeout=5)

    print("stopped.", flush=True)
    return 0
