"""Provide the Hatch version-source integration."""

from pathlib import Path
from typing import Any, final

from hatchling.version.core import VersionFile
from hatchling.version.source.plugin.interface import VersionSourceInterface
from packaging.version import InvalidVersion, Version

from versiondetail.get_version_details import (
    DEFAULT_FORMAT,
    DEFAULT_PATTERN,
    VALID_METHODS,
    VALID_SEGMENTS,
    VersionDetails,
)


@final
class VersionDetailVersionSource(VersionSourceInterface):
    """Resolve and update project versions through Hatch."""

    PLUGIN_NAME = "versiondetail"

    @property
    def options(self) -> dict[str, Any]:
        """Return the configured version-source options."""
        options = self.config.get("options", {})

        if not isinstance(options, dict):
            raise TypeError("Option 'options' must be a dictionary.")

        return options

    @property
    def mode(self) -> str:
        """Return the configured version resolution mode."""
        mode = self.options.get("mode", "regex")

        if not isinstance(mode, str):
            raise TypeError("Option 'mode' must be a string.")

        if mode not in VALID_METHODS:
            raise ValueError(f"Invalid mode {mode!r}. Expected one of: {', '.join(VALID_METHODS)}.")

        return mode

    @property
    def readfile(self) -> str:
        """Return the project-relative version file reference."""
        readfile = self.options.get("readfile", "")

        if not isinstance(readfile, str):
            raise TypeError("Option 'readfile' must be a string.")

        return readfile

    @property
    def pattern(self) -> str:
        """Return the regular expression used to read file versions."""
        pattern = self.options.get("pattern", DEFAULT_PATTERN)

        if not isinstance(pattern, str):
            raise TypeError("Option 'pattern' must be a string.")

        if "?P<version>" not in pattern:
            raise ValueError("Option 'pattern' must contain a named group 'version'.")

        return pattern

    @property
    def formatString(self) -> str:
        """Return the final version format string."""
        format_str = self.options.get("format", DEFAULT_FORMAT)

        if not isinstance(format_str, str):
            raise TypeError("Option 'format' must be a string.")

        return format_str

    @property
    def fallback(self) -> str:
        """Return the fallback base version."""
        fallback = self.options.get("fallback", "0.0.0")

        if not isinstance(fallback, str):
            raise TypeError("Option 'fallback' must be a string.")

        return fallback

    @property
    def segment(self) -> str:
        """Return the configured PEP 440 version segment."""
        segment = self.options.get("segment", "")

        if not isinstance(segment, str):
            raise TypeError("Option 'segment' must be a string.")

        if segment not in VALID_SEGMENTS:
            raise ValueError(f"Invalid segment {segment!r}. Expected one of: {', '.join(VALID_SEGMENTS)}.")

        return segment

    def get_version_data(self) -> dict[str, str]:
        """Return version data using Hatchling's required plugin API."""
        details = VersionDetails(
            root=Path(self.root),
            method=self.mode,
            readfile=self.readfile,
            pattern=self.pattern,
            format=self.formatString,
            fallback=self.fallback,
            segment=self.segment,
        ).getVersion()

        try:
            version = self.formatString.format(segment=self.segment, **details.toDict())
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Could not expand version format {self.formatString!r}: {exc}") from exc

        try:
            Version(version)
        except InvalidVersion as exc:
            raise ValueError(f"Expanded version is not PEP 440 compatible: {version!r}") from exc

        return {**details.toDict(), "version": version}

    def set_version(self, version: str, version_data: dict[str, Any]) -> None:
        """Write a new version to a regex-backed version file.

        Args:
            version: New base version.
            version_data: Existing version data supplied by Hatch.

        Raises:
            NotImplementedError: If the configured mode cannot write versions.
        """
        del version_data

        if self.mode not in {"regex", "multi"}:
            raise NotImplementedError(f"Mode {self.mode!r} cannot write versions.")

        if not self.readfile or ":" in self.readfile:
            raise NotImplementedError("Writing versions requires a plain file path.")

        version_file = VersionFile(self.root, self.readfile)
        version_file.read(pattern=self.pattern)
        version_file.set_version(version)
