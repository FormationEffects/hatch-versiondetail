"""Tests for the Hatch version-source adapter."""

from pathlib import Path

import pytest

from versiondetail.version_source import VersionDetailVersionSource


def test_get_version_data_withFormat_expandsVersionFields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Expand the configured version into a valid PEP 440 string."""
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "1.2.3"\n', encoding="utf-8")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    source = VersionDetailVersionSource(
        str(tmp_path),
        {
            "options": {
                "mode": "multi",
                "readfile": "version.py",
                "format": "{version}{segment}+{date}.{time}",
                "segment": "dev",
            }
        },
    )

    result = source.get_version_data()

    assert result["version"] == "1.2.3dev+1970-01-01.00-00-00"
    assert result["date"] == "1970-01-01"
    assert result["time"] == "00-00-00"


def test_set_version_withRegexMode_updatesVersionFile(tmp_path: Path) -> None:
    """Write a new version through Hatch's version-source API."""
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "1.2.3"\n', encoding="utf-8")

    source = VersionDetailVersionSource(
        str(tmp_path),
        {
            "options": {
                "mode": "regex",
                "readfile": "version.py",
            }
        },
    )

    source.set_version("2.0.0", {})

    assert version_file.read_text(encoding="utf-8") == 'VERSION = "2.0.0"\n'


def test_get_version_data_withUnknownField_raisesValueError(tmp_path: Path) -> None:
    """Report unknown format fields as configuration errors."""
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "1.2.3"\n', encoding="utf-8")

    source = VersionDetailVersionSource(
        str(tmp_path),
        {
            "options": {
                "mode": "regex",
                "readfile": "version.py",
                "format": "{unknown}",
            }
        },
    )

    with pytest.raises(ValueError, match="Could not expand version format"):
        source.get_version_data()
