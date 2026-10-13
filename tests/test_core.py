"""Tests for autofile.core — classify, scan, plan, conflict handling, execute."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from autofile import core  # noqa: E402

RULES = {
    "images": [".jpg", ".png"],
    "documents": [".pdf", ".txt"],
    "archives": [".zip"],
}


@pytest.fixture()
def ext_index() -> dict[str, str]:
    return core.build_ext_index(RULES)


def test_classify_known_extensions(ext_index):
    assert core.classify("photo.JPG", ext_index) == "images"
    assert core.classify("notes.txt", ext_index) == "documents"
    assert core.classify("dump.zip", ext_index) == "archives"


def test_classify_falls_back_to_other(ext_index):
    assert core.classify("mystery.xyz", ext_index) == core.OTHER
    assert core.classify("noextension", ext_index) == core.OTHER


def test_scan_takes_only_loose_top_level_files(tmp_path, ext_index):
    (tmp_path / "loose.pdf").write_text("x")
    (tmp_path / ".hidden.png").write_text("x")
    (tmp_path / "node_modules").mkdir()  # directory: never touched
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "index.js").write_text("x")
    (tmp_path / "AUTOFILE").mkdir()  # ignore_names match, case-insensitive

    found = core.scan(tmp_path, ext_index, {"autofile"})

    assert [p.name for p in found] == ["loose.pdf"]


def test_conflict_free_renames_never_overwrites(tmp_path):
    dst = tmp_path / "file.pdf"
    dst.write_text("original")
    resolved = core.conflict_free(dst)
    assert resolved.name == "file (2).pdf"
    (tmp_path / "file (2).pdf").write_text("second")
    assert core.conflict_free(dst).name == "file (3).pdf"


def test_plan_routes_by_category(tmp_path, ext_index):
    src = tmp_path / "shot.png"
    src.write_text("x")
    moves = core.plan([src], tmp_path, "_sorted", ext_index)
    assert len(moves) == 1
    assert moves[0].category == "images"
    assert moves[0].dst == tmp_path / "_sorted" / "images" / "shot.png"


def test_execute_moves_approved_and_skips_declined(tmp_path, ext_index):
    a, b = tmp_path / "a.pdf", tmp_path / "b.png"
    a.write_text("x")
    b.write_text("x")
    moves = core.plan([a, b], tmp_path, "_sorted", ext_index)
    log = tmp_path / "autofile.log"

    moved, skipped = core.execute(moves, log, approve=lambda m: m.src.name == "a.pdf")

    assert (moved, skipped) == (1, 1)
    assert (tmp_path / "_sorted" / "documents" / "a.pdf").exists()
    assert b.exists()  # declined: untouched
    assert "a.pdf" in log.read_text(encoding="utf-8")


def test_execute_renames_on_conflict(tmp_path, ext_index):
    src = tmp_path / "a.pdf"
    src.write_text("new")
    bin_dir = tmp_path / "_sorted" / "documents"
    bin_dir.mkdir(parents=True)
    (bin_dir / "a.pdf").write_text("old")

    moves = core.plan([src], tmp_path, "_sorted", ext_index)
    core.execute(moves, tmp_path / "autofile.log", approve=lambda m: True)

    assert (bin_dir / "a.pdf").read_text() == "old"  # original preserved
    assert (bin_dir / "a (2).pdf").read_text() == "new"
