"""Resolve versions from files, Git metadata, hashes, and reproducible timestamps."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from hatchling.version.core import VersionFile
from packaging.version import InvalidVersion, Version

from versiondetail.git import gitRevision, haveGit, isGitRepo

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

DEFAULT_PATTERN = r'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<version>.+?)\2'
DEFAULT_FORMAT = "{version}"
VALID_METHODS = ("regex", "script", "git", "hash", "date", "time", "multi")
VALID_SEGMENTS = (
    "",
    "a",
    "alpha",
    "b",
    "beta",
    "c",
    "rc",
    "pre",
    "preview",
    "r",
    "rev",
    "post",
    "dev",
    "p",
    "patch",
)


@dataclass(frozen=True)
class CustomSemVer:
    """Version values available to the configured format string."""

    version: str = ""
    git_short: str = ""
    git_long: str = ""
    date: str = ""
    time: str = ""
    hash: str = ""

    def toDict(self) -> dict[str, str]:
        """Return the values as format-string fields."""
        return {
            "version": self.version,
            "git_short": self.git_short,
            "git_long": self.git_long,
            "date": self.date,
            "time": self.time,
            "hash": self.hash,
        }


@dataclass
class VersionDetails:
    """Resolve version information from project files and repository metadata.

    Args:
        root: Project root directory.
        method: Version resolution method.
        readfile: Relative file path, optionally followed by `:functionName`.
        pattern: Regular expression containing a named `version` group.
        format: Version format retained for compatibility with the version source.
        fallback: Version used when no file-derived version is available.
        segment: Optional PEP 440 version segment.
    """

    root: Path
    method: str = field(default="multi")
    readfile: str = field(default="")
    pattern: str = field(default=DEFAULT_PATTERN)
    format: str = field(default=DEFAULT_FORMAT)
    fallback: str = field(default="0.0.0")
    segment: str = field(default="")

    def __post_init__(self):
        self.root = Path(self.root).resolve()

        if self.method not in VALID_METHODS:
            raise ValueError(f"Invalid method {self.method!r}. Expected one of: {', '.join(VALID_METHODS)}.")

        if self.segment not in VALID_SEGMENTS:
            raise ValueError(f"Invalid segment {self.segment!r}. Expected one of: {', '.join(VALID_SEGMENTS)}.")

        if self.method in {"regex", "script", "hash"} and not self.readfile:
            raise ValueError(f"Method {self.method!r} requires the `readfile` option.")

    def _splitFileReference(self) -> tuple[str, str]:
        """Split `path.py:functionName` into its components."""
        file_path, separator, function_name = self.readfile.rpartition(":")

        if separator:
            return file_path, function_name

        return self.readfile, ""

    def _resolveFilePath(self) -> Path:
        """Resolve the configured file relative to the project root."""
        file_path, _ = self._splitFileReference()
        resolved_path = (self.root / file_path).resolve()

        if not resolved_path.is_file():
            raise FileNotFoundError(f"Version file does not exist: {resolved_path}")

        return resolved_path

    def _readRegexVersion(self) -> str:
        """Read a version using Hatchling's version-file parser."""
        file_path, _ = self._splitFileReference()
        return VersionFile(str(self.root), file_path).read(pattern=self.pattern)

    def _loadScriptModule(self, module_path: Path) -> ModuleType:
        """Load a Python module from a project-relative path."""
        spec = importlib.util.spec_from_file_location("_hatch_versiondetail_source", module_path)

        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load version module: {module_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _readScriptVersion(self) -> str:
        """Call the configured version function."""
        module_path = self._resolveFilePath()
        _, function_name = self._splitFileReference()

        if not function_name:
            raise ValueError("Script version references must use 'path/to/module.py:functionName'.")

        module = self._loadScriptModule(module_path)
        function = getattr(module, function_name, None)

        if not callable(function):
            raise TypeError(f"Version function {function_name!r} is not callable in {module_path}.")

        version_function: Callable[[], object] = function
        result = version_function()

        if not isinstance(result, str):
            raise TypeError(f"Version function {function_name!r} must return str, got {type(result).__name__}.")

        return result

    def _getHighestVersion(self, *versions: str) -> str:
        """Return the highest valid PEP 440 version."""
        candidates = [version for version in versions if version]

        if not candidates:
            return self.fallback

        try:
            return max(candidates, key=Version)
        except InvalidVersion as exc:
            raise ValueError(f"Invalid PEP 440 version: {exc}.") from exc

    def _getGitRevision(self) -> tuple[str, str]:
        """Return the full and abbreviated Git revisions."""
        if not haveGit() or not isGitRepo(self.root):
            return "", ""

        revision = gitRevision(self.root)
        return revision, revision[:7]

    def _getFileHash(self) -> str:
        """Return the SHA-256 hash of the configured version file."""
        return hashlib.sha256(self._resolveFilePath().read_bytes()).hexdigest()

    def _getBuildTime(self) -> datetime:
        """Return the reproducible UTC build time."""
        source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")

        if source_date_epoch is None:
            return datetime.now(UTC)

        try:
            timestamp = int(source_date_epoch)
        except ValueError as exc:
            raise ValueError("SOURCE_DATE_EPOCH must be an integer Unix timestamp.") from exc

        return datetime.fromtimestamp(timestamp, UTC)

    def getVersion(self) -> CustomSemVer:
        """Resolve all fields required by the version format.

        Returns:
            Resolved version, Git, timestamp, and source-hash fields.
        """
        regex_version = ""
        script_version = ""

        if self.method in {"regex", "multi"} and self.readfile:
            regex_version = self._readRegexVersion()

        if self.method in {"script", "multi"} and ":" in self.readfile:
            script_version = self._readScriptVersion()

        version = self._getHighestVersion(regex_version, script_version)
        build_time = self._getBuildTime()

        if self.method == "date":
            version = build_time.strftime("%Y.%m.%d")
        elif self.method == "time":
            version = build_time.strftime("%H.%M.%S")

        git_long = ""
        git_short = ""

        if self.method in {"git", "multi"}:
            git_long, git_short = self._getGitRevision()

        file_hash = ""
        if self.method in {"hash", "multi"} and self.readfile:
            file_hash = self._getFileHash()

        return CustomSemVer(
            version=version,
            git_short=git_short,
            git_long=git_long,
            date=build_time.strftime("%Y-%m-%d"),
            time=build_time.strftime("%H-%M-%S"),
            hash=file_hash,
        )
