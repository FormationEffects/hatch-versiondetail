"""Git utilities, adopted from mypy's git utilities (https://github.com/python/mypy/blob/master/mypy/git.py)."""

from __future__ import annotations

import subprocess  # nosec
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def isGitRepo(dir: Path) -> bool:
    """Is the given directory version-controlled with git?"""
    return dir.joinpath(".git").exists()


def haveGit() -> bool:
    """Can we run the git executable?"""
    try:
        subprocess.check_output(["git", "--help"])  # nosec
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def gitRevision(dir: Path) -> str:
    """Get the SHA-1 of the HEAD of a git repository."""
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dir).decode("utf-8").strip()  # nosec
