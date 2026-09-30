"""Register hatch-versiondetail plugins with Hatch."""

from hatchling.plugin import hookimpl

from versiondetail.build_hook import VersionDetailBuildHook
from versiondetail.version_source import VersionDetailVersionSource


@hookimpl
def hatch_register_version_source() -> type[VersionDetailVersionSource]:
    """Register the version-source plugin."""
    return VersionDetailVersionSource


@hookimpl
def hatch_register_build_hook() -> type[VersionDetailBuildHook]:
    """Register the optional Nuitka build hook."""
    return VersionDetailBuildHook
