"""Tests for version detail resolution."""

import hashlib
from pathlib import Path

import pytest

from versiondetail.get_version_details import VersionDetails


def test_getVersion_withMultiMode_returnsAllExpansionFields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve the highest file version and reproducible metadata."""
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "1.2.3"\n\ndef buildVersion() -> str:\n    return "2.0.0"\n', encoding="utf-8")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    result = VersionDetails(root=tmp_path, method="multi", readfile="version.py:buildVersion").getVersion()

    assert result.version == "2.0.0"
    assert result.date == "1970-01-01"
    assert result.time == "00-00-00"
    assert result.hash == hashlib.sha256(version_file.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("date", "1970.01.01"),
        ("time", "00.00.00"),
    ],
)
def test_getVersion_withTimestampMode_returnsPep440Version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, expected: str) -> None:
    """Convert a reproducible timestamp into a numeric version."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    result = VersionDetails(root=tmp_path, method=method).getVersion()

    assert result.version == expected


def test_getVersion_withInvalidSourceDateEpoch_raisesValueError(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject malformed reproducible-build timestamps."""
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "invalid")

    with pytest.raises(ValueError, match="SOURCE_DATE_EPOCH must be an integer"):
        VersionDetails(root=tmp_path, method="date").getVersion()


def test_getVersion_withMissingScriptFunction_raisesTypeError(tmp_path: Path) -> None:
    """Reject script references that do not resolve to callables."""
    version_file = tmp_path / "version.py"
    version_file.write_text('VERSION = "1.2.3"\n', encoding="utf-8")

    with pytest.raises(TypeError, match="is not callable"):
        VersionDetails(root=tmp_path, method="script", readfile="version.py:missingFunction").getVersion()
