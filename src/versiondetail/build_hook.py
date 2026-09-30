"""Compile package modules with Nuitka during Hatch wheel builds."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, final

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


@final
class VersionDetailBuildHook(BuildHookInterface):
    """Optionally compile Python modules for wheel builds."""

    PLUGIN_NAME = "versiondetail"

    @property
    def output_directory(self) -> Path:
        """Return the directory containing generated extension modules."""
        return Path(self.root, "build", "versiondetail-nuitka")

    def clean(self, versions: list[str]) -> None:
        """Remove generated Nuitka artifacts."""
        del versions
        shutil.rmtree(self.output_directory, ignore_errors=True)

    def _getPackages(self) -> list[str]:
        """Return the configured packages to compile."""
        packages = self.config.get("packages", [])

        if not isinstance(packages, list) or not all(isinstance(package, str) and package for package in packages):
            raise TypeError("Option 'packages' must be a list of package names.")

        if not packages:
            raise ValueError("Nuitka compilation requires at least one package.")

        return packages

    def _getExtraArguments(self) -> list[str]:
        """Return additional arguments passed directly to Nuitka."""
        arguments = self.config.get("nuitka-args", [])

        if not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in arguments):
            raise TypeError("Option 'nuitka-args' must be a list of strings.")

        return arguments

    def _findCompiledModule(self, output_dir: Path, module_name: str) -> Path:
        """Find the extension module produced by Nuitka."""
        candidates = [path for path in output_dir.glob(f"{module_name}.*") if path.suffix in {".pyd", ".so"}]

        if len(candidates) != 1:
            raise RuntimeError(f"Expected one compiled module for {module_name!r}, found {len(candidates)} in {output_dir}.")

        return candidates[0]

    def _compileModule(self, source_file: Path, output_dir: Path, extra_arguments: list[str]) -> Path:
        """Compile one Python module with Nuitka."""
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "nuitka",
            "--module",
            str(source_file),
            f"--output-dir={output_dir}",
            "--remove-output",
            "--no-pyi-file",
            *extra_arguments,
        ]

        self.app.display_info(f"[versiondetail] Compiling {source_file}")

        subprocess.run(command, cwd=source_file.parent, check=True)

        return self._findCompiledModule(output_dir, source_file.stem)

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Compile configured packages before building a wheel."""
        if self.target_name != "wheel" or version == "editable":
            return

        compile_source = self.config.get("compile", False)

        if not isinstance(compile_source, bool):
            raise TypeError("Option 'compile' must be a boolean.")

        if not compile_source:
            return

        if importlib.util.find_spec("nuitka") is None:
            raise RuntimeError("Nuitka compilation requires 'hatch-versiondetail[nuitka]'.")

        working_directory = self.config.get("working-directory", "src")
        if not isinstance(working_directory, str):
            raise TypeError("Option 'working-directory' must be a string.")

        source_root = Path(self.root, working_directory).resolve()
        extra_arguments = self._getExtraArguments()
        force_include: dict[str, str] = {}

        self.clean([])

        for package in self._getPackages():
            package_path = (source_root / package).resolve()

            if not package_path.is_relative_to(source_root) or not package_path.is_dir():
                raise ValueError(f"Package directory does not exist: {package_path}")

            source_files = sorted(path for path in package_path.rglob("*.py") if path.name != "__init__.py")

            if not source_files:
                raise ValueError(f"Package contains no compilable modules: {package}")

            for source_file in source_files:
                relative_parent = source_file.parent.relative_to(source_root)
                output_dir = self.output_directory / relative_parent
                compiled_module = self._compileModule(source_file, output_dir, extra_arguments)
                wheel_path = (relative_parent / compiled_module.name).as_posix()
                force_include[str(compiled_module)] = wheel_path

        build_data["force_include"].update(force_include)
        build_data["infer_tag"] = True
        build_data["pure_python"] = False
