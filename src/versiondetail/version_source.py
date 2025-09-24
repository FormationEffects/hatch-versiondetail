from typing import Any

from hatchling.version.source.plugin.interface import VersionSourceInterface

from versiondetail.get_version_details import VersionDetails


class VersionDetailVersionSource(VersionSourceInterface):
    PLUGIN_NAME = "versiondetail"

    def __init__(self, root: str, config: dict[str, Any]):
        super().__init__(root, config)

    @property
    def options(self):
        options = self.config.get("options", {})
        if not isinstance(options, dict):
            raise TypeError("Option 'options' must be a dictionary.")
        return options

    @property
    def mode(self):
        mode = self.options.get("mode", "regex")
        if not isinstance(mode, str):
            raise TypeError("Option 'mode' must be a string.")
        if mode not in ["regex", "script", "git", "hash", "date", "time", "multi"]:
            raise ValueError(f"Invalid mode '{mode}' specified. Must be one of: 'regex', 'script', 'git', 'hash', 'date', 'time', 'multi'.")
        return mode

    @property
    def readfile(self):
        readfile = self.options.get("readfile", "")
        if not isinstance(readfile, str):
            raise TypeError("Option 'readfile' must be a string.")
        return readfile

    @property
    def pattern(self):
        pattern = self.options.get("pattern", r'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<version>.+?)\2')
        if not isinstance(pattern, str):
            raise TypeError("Option 'pattern' must be a string.")
        if "?P<version>" not in pattern:
            raise ValueError("Option 'pattern' must contain a named group 'version'.")
        return pattern

    @property
    def format(self):
        format_str = self.options.get("format", "{version}")
        if not isinstance(format_str, str):
            raise TypeError("Option 'format' must be a string.")
        return format_str

    @property
    def fallback(self):
        fallback = self.options.get("fallback", "0.0.0")
        if not isinstance(fallback, str):
            raise TypeError("Option 'fallback' must be a string.")
        return fallback

    @property
    def segment(self):
        segment = self.options.get("segment", "")
        if not isinstance(segment, str):
            raise TypeError("Option 'segment' must be a string.")
        if segment not in ["", "a", "alpha", "b", "beta", "c", "rc", "pre", "preview", "r", "rev", "post", "dev", "p", "patch"]:
            raise ValueError(f"Invalid segment '{segment}' specified. Must be one of: '', 'a', 'alpha', 'b', 'beta', 'c', 'rc', 'pre', 'preview', 'r', 'rev', 'post', 'dev', 'p', 'patch'.")
        return segment

    def get_version_data(self):
        custom_semver = VersionDetails(self.root, self.mode, self.readfile, self.pattern, self.format, self.fallback, self.segment).get_version()

        formatted_version = self.format.format(segment=self.segment, **custom_semver.toDict())

        return {"version": formatted_version}

    def get_template_fields(self) -> dict[str, Any] | None:
        return self.__fields
