import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from hatchling.bridge.app import Application
from hatchling.builders.config import BuilderConfigBound
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.core import ProjectMetadata

from versiondetail.version_source import VersionDetailVersionSource


class VersionDetailBuildHook(BuildHookInterface):
    PLUGIN_NAME = "versiondetail"

    def __init__(self, root: str, config: dict[str, Any], build_config: BuilderConfigBound, metadata: ProjectMetadata, directory: str, target_name: str, app: Application | None = None) -> None:
        super().__init__(root, config, build_config, metadata, directory, target_name, app)
        self.__output_dir: Path | None = None

    @property
    def output_dir(self) -> Path:
        """Get the output directory for the build."""
        if self.__output_dir is None:
            self.__output_dir = Path(self.root, "build", "nuitka")
        return self.__output_dir

    @property
    def artifact_patterns(self) -> list[str]:
        """Get the patterns for the artifacts produced by this build hook."""
        return ["**/*.whl", "**/*.tar.gz"]

    def get_inclusion_map(self) -> dict[str, str]:
        """Get the inclusion map for the build artifacts."""
        inclusion_map = {}
        for path in self.output_dir.glob("*"):
            inclusion_map[str(path)] = str(path.relative_to(self.output_dir))

        return inclusion_map

    def compile_module(self, package: str, output_dir: Path, source_path: Path) -> subprocess.Popen:
        """Compile the package as a module using Nuikta."""

        args = [
            "--module",
            f"{package}",
            f"--include-package={package}",
            f"--include-package-data={package}",
            f"--output-dir={output_dir}",
            "--remove-output",
        ]

        self.app.display_info("[VERSIONDETAIL:BUILD] | Compiling as module with Nuikta...")
        process = subprocess.Popen([sys.executable, "-m", "nuitka", *args], cwd=source_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # nosec

        while True:
            if not process.stdout:
                break

            line = process.stdout.readline()

            if not line:
                break

            self.app.display_info(f"[VERSIONDETAIL:BUILD:NUITKA] | {line.strip()}")
        # Remove .py files to exclude them from the wheel

        process.wait()

        for py_file in output_dir.rglob("*.py"):
            self.app.display_info(f"[VERSIONDETAIL:BUILD] | Removing source file: {py_file}")
            py_file.unlink()

        return process

    def compile_all_modules(self, package: str, output_dir: Path, src_path: Path) -> tuple[int, str]:
        """
        Recursively compile all .py files in the package directory tree.
        """

        """Compile single files in the package using Nuitka."""
        py_files = [p for p in src_path.rglob("*.py")]

        for file in py_files:
            parent_dir = file.parent
            parent_dir.mkdir(parents=True, exist_ok=True)

            args = [
                "--module",
                f"{package}",
                f"--output-dir={output_dir}",
                "--remove-output",
            ]
            subprocess.run([sys.executable, "-m", "nuitka", *args, str(file)], check=True, cwd=parent_dir)  # nosec

        print("[DEBUG NUITKA] Compiling single files:", py_files)
        return 0, "Nuitka single file compilation not implemented yet."

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """
        Called before the build process starts.
        """

        if self.target_name != "wheel":
            return

        if os.environ.get("UV_SKIP_HOOKS") == "1":
            return

        compile_source = self.config.get("compile", False)
        build_mode = self.config.get("build_mode", "module")
        packages = self.config.get("packages", [])
        source_path = self.config.get("working-directory", "src")

        if not compile_source:
            return

        self.app.display_info(f"[VERSIONDETAIL:BUILD] | Initializing Nuikta build hook for version: {version}")

        src_path = Path(self.root, source_path)

        if not packages:
            candidates = [dir for dir in src_path.iterdir() if dir.is_dir()]
            if not candidates:
                raise RuntimeError(f"No source directories found in {src_path}. Please specify a 'package' in the configuration.")
            packages = [str(dir.name) for dir in candidates]

        for package in packages:
            source_path = src_path / package
            if not source_path.exists() or not source_path.is_dir():
                self.app.display_error(f"[VERSIONDETAIL:BUILD] | Source path {source_path} does not exist or is not a directory.")
                continue

            output_dir = self.output_dir / package
            output_dir.mkdir(parents=True, exist_ok=True)

            if build_mode == "standalone":
                self.compile_standalone(package, output_dir, source_path)
            elif build_mode == "module":
                self.compile_module(package, output_dir, src_path)
            elif build_mode == "custom":
                self.compile_all_modules(package, output_dir, src_path)
            else:
                raise ValueError(f"Invalid build mode '{build_mode}' specified. Must be one of: 'standalone', 'module', 'custom'.")

            self.app.display_info(f"[VERSIONDETAIL:BUILD] | Successfully compiled {package} with Nuikta.")

        self.app.display_info("[VERSIONDETAIL:BUILD] | Build hook initialized successfully.")

        build_data["infer_tag"] = True
        build_data["pure_python"] = False
        build_data["artifacts"].extend(self.artifact_patterns)
        build_data["force_include"] = self.get_inclusion_map()

        print(f"[VERSIONDETAIL] | Build data: {build_data}")

        # if not isinstance(version_source, VersionDetailVersionSource):
        #     self.app.display_warning(f"Versiondetail build hook should only be used with 'versiondetail' version source, but found {self.metadata.hatch.version.source_name!r}.")
        #     version_source = VersionDetailVersionSource(self.root, self.metadata.hatch.version.config)

    # def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
    #     #     """
    #     print(f"[VERSIONDETAIL] | Tag B: {build_data.get('tag', 'N/A')}")
    #     print(f"[VERSIONDETAIL] | Build Data B: {build_data}")
    #     build_data["tag"] = "custom-tag"

    #     Called after the wheel metadata and files have been prepared,
    #     but before the wheel file is finalized.
    #     """
    #     if self.target_name == "wheel" and version == "editable":
    #         print("Not running onbuild step for editable build")
    #         return None

    #     version_source = self.metadata.hatch.version.source

    #     if not isinstance(version_source, VersionDetailVersionSource):
    #         raise RuntimeError(f"versiondetail-onbuild can only be used with 'versiondetail' version source, but version source is {self.metadata.hatch.version.source_name!r}")

    #     template_fields = version_source.get_template_fields()
    #     if template_fields is None:
    #         print("Appear to be building from an sdist; not running onbuild step")
    #         return

    #     print(f"[VERSIONDETAIL] | Running build hook for version: {version_source}")
