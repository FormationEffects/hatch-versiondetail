import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from hatchling.version.core import VersionFile

from versiondetail.git import gitRevision, haveGit, isGitRepo

DEFAULT_PATTERN = r'(?i)^(__version__|VERSION) *= *([\'"])v?(?P<version>.+?)\2'
DEFAULT_FORMAT = "{version}"


class CustomVersionFile:
    def __init__(self, input_file: tuple[str, str] | str):
        self.module_path = input_file[0]
        self.function_name = input_file[1]

    def read(self) -> str:
        try:
            # Import the module dynamically
            spec = importlib.util.spec_from_file_location("version_module", str(self.module_path))
            module = importlib.util.module_from_spec(spec)
            sys.modules["version_module"] = module
            spec.loader.exec_module(module)

            if not self.function_name:
                return ""
            func = getattr(module, self.function_name)
            return func()
        except Exception as ex:
            print(f"Error reading version from file {self.module_path}: {ex}")
            return ""


@dataclass
class CustomSemVer:
    version: str = ""
    git_short: str = ""
    git_long: str = ""
    date: str = ""
    time: str = ""
    hash: str = ""

    def toDict(self) -> dict:
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
    root: Path
    method: str = field(default="multi")
    readfile: str = field(default="")
    pattern: str = field(default=DEFAULT_PATTERN)
    format: str = field(default=DEFAULT_FORMAT)
    fallback: str = field(default="0.0.0")
    segment: str = field(default="")

    def __post_init__(self):
        self.root = Path(self.root)

        # Validate method
        if not isinstance(self.method, str):
            raise TypeError("Option 'method' must be a string.")
        if self.method not in ["regex", "script", "git", "hash", "date", "time", "multi"]:
            raise ValueError(f"Invalid method '{self.method}' specified. Must be one of: 'regex', 'script', 'git', 'hash', 'date', 'time', 'multi'.")

        # Validate readfile
        if self.method in ["regex", "script"] and not self.readfile:
            raise ValueError("Option 'readfile' must be specified for regex, script, or multi methods.")

        if not isinstance(self.segment, str):
            raise TypeError("Option 'segment' must be a string.")
        if self.segment not in ["", "a", "alpha", "b", "beta", "c", "rc", "pre", "preview", "r", "rev", "post", "dev", "p", "patch"]:
            raise ValueError(f"Invalid segment '{self.segment}' specified. Must be one of: '', 'a', 'alpha', 'b', 'beta', 'c', 'rc', 'pre', 'preview', 'r', 'rev', 'post', 'dev', 'p', 'patch'.")

    def _parse_file_from_path(self, file_path: str) -> tuple[Path, str]:
        function_name = ""
        module_path = Path()
        if file_path.endswith((".py", ".pyi")):
            function_name = ""
            module_path = Path(file_path).resolve()
        elif ":" in file_path:
            module, function = file_path.split(":")
            for mod_ext in [".py", ".pyi"]:
                module = Path(f"{module}{mod_ext}")
                if module.exists():
                    function_name = function
                    module_path = module.resolve()
                    break
        return module_path, function_name

    def _git_parse(self, dir: str) -> str:
        """Placeholder for git parsing logic."""
        # This function should implement the logic to retrieve the version from git
        dir = Path(dir).resolve()
        if not haveGit():
            return {"long": "0", "short": "0"}

        if not isGitRepo(dir):
            return {"long": "0", "short": "0"}

        git_revision = gitRevision(dir)

        return {"long": git_revision, "short": git_revision[:7]}

    def _get_higher_semver(self, *versions) -> str:
        """Compare two semantic versions and return the higher one."""
        ver_comp = [vv for vv in versions if isinstance(vv, str) and vv != ""]

        if not ver_comp:
            return self.fallback

        version_tuples = [(tuple(map(int, v.split("."))), v) for v in ver_comp]
        # Sort by tuple
        highest = max(version_tuples)
        return highest[1]

    def get_version(self) -> CustomSemVer:
        semver = CustomSemVer()
        regex_version = ""
        script_version = ""

        if self.method == "regex" or self.method == "multi":
            if not self.readfile and self.method != "multi":
                raise ValueError("Option 'readfile' must be specified for regex, or multi methods.")
            module_path, _ = self._parse_file_from_path(self.readfile)
            if not module_path.exists() and self.method != "multi":
                raise FileNotFoundError(f"File {module_path} does not exist.")
            try:
                regex_version = VersionFile(self.root, module_path).read(pattern=self.pattern)
            except Exception as e:
                print(f"[VERSIONDETAIL] | Error reading version from file {module_path}: {e}")
                regex_version = ""

        if self.method == "script" or self.method == "multi":
            if not self.readfile and self.method != "multi":
                raise ValueError("Option 'readfile' must be specified for script, or multi methods.")
            script_version = CustomVersionFile(input_file=self._parse_file_from_path(self.readfile)).read()

        if regex_version and script_version:
            semver.version = self._get_higher_semver(regex_version, script_version)
        elif regex_version:
            semver.version = regex_version
        elif script_version:
            semver.version = script_version
        else:
            semver.version = self.fallback

        if self.method == "git" or self.method == "multi":
            git_hash = self._git_parse(self.root)
            if git_hash:
                semver.git_short = git_hash["short"]
                semver.git_long = git_hash["long"]
            else:
                semver.git_short = "0"
                semver.git_long = "0"

        if self.method == "hash" or self.method == "multi":
            semver.hash = "00"

        # Because date and time are not directly related to the version, we can use them as additional information
        now = datetime.now()
        semver.date = now.strftime("%Y-%m-%d")
        semver.time = now.strftime("%H-%M-%S")

        return semver
