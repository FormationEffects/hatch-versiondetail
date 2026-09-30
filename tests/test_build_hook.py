"""Tests for the optional Nuitka build hook."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest

from versiondetail.build_hook import VersionDetailBuildHook

if TYPE_CHECKING:
    from pathlib import Path


def createBuildHook(root: Path, config: dict[str, Any]) -> VersionDetailBuildHook:
    """Create a build hook without requiring a complete Hatch build."""
    return VersionDetailBuildHook(
        root=str(root),
        config=config,
        build_config=cast("Any", None),
        metadata=cast("Any", None),
        directory=str(root / "dist"),
        target_name="wheel",
    )


def test_initialize_withCompilation_addsCompiledModulesToWheel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Compile package modules and register their wheel destinations."""
    package_path = tmp_path / "src" / "example"
    package_path.mkdir(parents=True)
    (package_path / "__init__.py").write_text("", encoding="utf-8")
    (package_path / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    hook = createBuildHook(tmp_path, {"compile": True, "packages": ["example"]})

    monkeypatch.setattr("versiondetail.build_hook.importlib.util.find_spec", lambda name: object())

    def compileModule(source_file: Path, output_dir: Path, extra_arguments: list[str]) -> Path:
        assert source_file.name == "module.py"
        assert extra_arguments == []

        output_dir.mkdir(parents=True, exist_ok=True)
        compiled_module = output_dir / "module.cp311-test.pyd"
        compiled_module.write_bytes(b"compiled")
        return compiled_module

    monkeypatch.setattr(hook, "_compileModule", compileModule)

    build_data: dict[str, Any] = {"force_include": {}, "infer_tag": False, "pure_python": True}

    hook.initialize("1.0.0", build_data)

    assert build_data["infer_tag"] is True
    assert build_data["pure_python"] is False
    assert list(build_data["force_include"].values()) == ["example/module.cp311-test.pyd"]


def test_initialize_withoutNuitka_raisesHelpfulError(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Explain which package extra enables compilation."""
    hook = createBuildHook(tmp_path, {"compile": True, "packages": ["example"]})

    monkeypatch.setattr("versiondetail.build_hook.importlib.util.find_spec", lambda name: None)

    build_data: dict[str, Any] = {"force_include": {}, "infer_tag": False, "pure_python": True}

    with pytest.raises(RuntimeError, match=r"hatch-versiondetail\[nuitka\]"):
        hook.initialize("1.0.0", build_data)
