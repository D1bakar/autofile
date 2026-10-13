"""Tests for watcher candidate filtering — the safety boundary of watch mode."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from autofile import watcher  # noqa: E402

IGNORE = {"autofile", "_sorted"}


def test_loose_top_level_file_is_candidate(tmp_path):
    f = tmp_path / "dump.pdf"
    f.write_text("x")
    assert watcher.is_candidate(f, tmp_path, IGNORE)


def test_directories_are_never_candidates(tmp_path):
    d = tmp_path / "project"
    d.mkdir()
    assert not watcher.is_candidate(d, tmp_path, IGNORE)


def test_nested_files_are_never_candidates(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    f = project / "data.csv"
    f.write_text("x")
    assert not watcher.is_candidate(f, tmp_path, IGNORE)


def test_files_inside_output_bins_are_never_candidates(tmp_path):
    bin_dir = tmp_path / "_sorted" / "images"
    bin_dir.mkdir(parents=True)
    f = bin_dir / "photo.png"
    f.write_text("x")
    assert not watcher.is_candidate(f, tmp_path, IGNORE)


def test_hidden_and_ignored_names_are_skipped(tmp_path):
    hidden = tmp_path / ".secret.pdf"
    hidden.write_text("x")
    ignored = tmp_path / "AUTOFILE"  # case-insensitive ignore
    ignored.write_text("x")
    assert not watcher.is_candidate(hidden, tmp_path, IGNORE)
    assert not watcher.is_candidate(ignored, tmp_path, IGNORE)


def test_nonexistent_path_is_not_candidate(tmp_path):
    assert not watcher.is_candidate(tmp_path / "ghost.pdf", tmp_path, IGNORE)
