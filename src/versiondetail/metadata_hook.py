from collections import ChainMap

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.utils.context import ContextStringFormatter

from versiondetail.git import gitRevision


class VersionDetailMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "versiondetail"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"[VERSIONDETAIL] | Metadata Hook A: {self.PLUGIN_NAME}")

    def update(self, metadata):
        self.get_known_classifiers()
        print(f"[VERSIONDETAIL] | Metadata Hook B: {self.PLUGIN_NAME}")
        print(f"[VERSIONDETAIL] | Classifiers: {self.get_known_classifiers()}")
        formatter = ContextStringFormatter(
            ChainMap(
                {
                    "commit_hash": lambda *args: gitRevision(self.root),
                }
            )
        )

        version = self.config.get("version", "")
        # if not version:
        #     raise ValueError(f"Option `version` for metadata hook `{self.PLUGIN_NAME}` is required")
        print(f"[VERSIONDETAIL] | Version: {metadata['version']}")
        print(f"[VERSIONDETAIL] | Metadata: {metadata}")
        # metadata["version"] = version

        # Update other metadata fields if needed
        additional_fields = self.config.get("additional_fields", {})
        if not isinstance(additional_fields, dict):
            raise TypeError(f"Option `additional_fields` for metadata hook `{self.PLUGIN_NAME}` must be a dictionary")

        metadata.update(ChainMap(additional_fields))
