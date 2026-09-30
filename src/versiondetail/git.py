"""Read version metadata from Git repositories.

Adopted from mypy's git utilities (https://github.com/python/mypy/blob/master/mypy/git.py).
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def haveGit() -> bool:
    """Return whether the Git executable is available."""
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False

    return True


def isGitRepo(directory: Path) -> bool:
    """Return whether a path belongs to a Git working tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False

    return result.stdout.strip() == "true"


def gitRevision(directory: Path) -> str:
    """Return the full commit hash at HEAD.

    Args:
        directory: Git working tree path.

    Returns:
        The full hexadecimal commit hash.

    Raises:
        RuntimeError: If Git cannot resolve HEAD.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=directory,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"Could not resolve Git revision for {directory}.") from exc

    return result.stdout.strip()
