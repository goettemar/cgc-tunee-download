"""Test orchestrator utilities."""

import os
import tempfile
from pathlib import Path

import pytest

from src.orchestrator import (
    _duration_display_to_folder,
    _folder_has_files,
    _sanitize,
    prepare_project,
)


def test_sanitize():
    """Test sanitize function."""
    assert _sanitize('foo"bar') == "foo_bar"
    assert _sanitize("foo:bar") == "foo_bar"
    assert _sanitize("foo/bar") == "foo_bar"
    assert _sanitize("foo<bar>") == "foo_bar_"
    assert _sanitize("normal") == "normal"


def test_duration_display_to_folder():
    """Test duration conversion."""
    assert _duration_display_to_folder("03:45") == "03m45s"
    assert _duration_display_to_folder("10:02") == "10m02s"
    assert _duration_display_to_folder("invalid") == "00m00s"


def test_folder_has_files():
    """Test folder_has_files detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Empty folder
        assert not _folder_has_files(tmpdir)

        # Add a song file
        Path(tmpdir, "test.mp3").touch()
        assert _folder_has_files(tmpdir)

        # Clean up
        os.remove(os.path.join(tmpdir, "test.mp3"))

        # Add non-song file
        Path(tmpdir, "readme.txt").touch()
        assert not _folder_has_files(tmpdir)


def test_prepare_project():
    """Test prepare_project creates correct folder structure."""
    songs = [
        {"name": "Test Song", "duration": "03:45"},
        {"name": "Another Song", "duration": "04:12"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        original_tunee_dir = os.path.join(os.path.expanduser("~"), "Downloads", "tunee")
        import src.orchestrator as orch

        orch.TUNEE_DIR = tmpdir

        try:
            result = prepare_project(songs)

            assert len(result) == 2
            assert result[0]["num"] == 1
            assert result[0]["name"] == "Test Song"
            assert result[0]["duration"] == "03m45s"
            assert "01 - Test Song - 03m45s" in result[0]["folder"]
            assert not result[0]["complete"]

            assert os.path.exists(os.path.join(tmpdir, result[0]["folder"]))
            assert os.path.exists(os.path.join(tmpdir, result[1]["folder"]))
        finally:
            orch.TUNEE_DIR = original_tunee_dir
