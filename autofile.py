#!/usr/bin/env python3
"""Entry point: python autofile.py [options]."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from autofile.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
