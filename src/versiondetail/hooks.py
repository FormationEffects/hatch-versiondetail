from hatchling.plugin import hookimpl

from versiondetail.build_hook import VersionDetailBuildHook
from versiondetail.metadata_hook import VersionDetailMetadataHook
from versiondetail.version_source import VersionDetailVersionSource


@hookimpl
def hatch_register_version_source():
    return VersionDetailVersionSource


@hookimpl
def hatch_register_metadata_hook():
    return VersionDetailMetadataHook


@hookimpl
def hatch_register_build_hook():
    return VersionDetailBuildHook
