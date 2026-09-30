# hatch-versiondetail

A Hatch plugin for building versions from source files, Git metadata, source hashes, and reproducible UTC timestamps.

Initially used internally to release updates, without having to continually version up patches, minor, and major versions.
Released publically for anyone else to use within their own projects.

## Requirements

- Python 3.11 or newer
- Hatchling 1.32.4 or newer
- Nuitka 4.2.2 or newer when optional module compilation is enabled

## Installation

Until the package is published to PyPI, add it to the consuming project's build requirements:

```toml
[build-system]
requires = [
    "hatchling>=1.32.4",
    "hatch-versiondetail @ git+https://github.com/FormationEffects/hatch-versiondetail.git",
]
build-backend = "hatchling.build"
```

After a PyPI release:

```toml
[build-system]
requires = [
    "hatchling>=1.32.4",
    "hatch-versiondetail>=0.2.0",
]
build-backend = "hatchling.build"
```

## File versions

Read a version from a Python file:

```toml
[tool.hatch.version]
source = "versiondetail"

[tool.hatch.version.options]
mode = "regex"
readfile = "src/example/version.py"
```

The default pattern recognizes either form:

```python
VERSION = "1.2.3"
__version__ = "1.2.3"
```

A custom pattern must contain a named `version` group:

```toml
pattern = '''^RELEASE = "(?P<version>[^"]+)"'''
```

## Script versions

Call a function from a project-relative Python file:

```toml
[tool.hatch.version.options]
mode = "script"
readfile = "src/example/version.py:buildVersion"
```

The function must take no arguments and return a string:

```python
def buildVersion() -> str:
    return "1.2.3"
```

## Expanded versions

Multi mode combines file, Git, hash, and timestamp metadata:

```toml
[tool.hatch.version.options]
mode = "multi"
readfile = "src/example/version.py"
format = "{version}{segment}+{date}.{time}.{git_short}"
segment = "dev"
fallback = "0.0.0"
```

Available format fields:

| Field | Value |
|---|---|
| `version` | Highest file or script version |
| `segment` | Configured PEP 440 segment |
| `git_short` | First seven characters of the Git revision |
| `git_long` | Full Git revision |
| `date` | UTC date as `YYYY-MM-DD` |
| `time` | UTC time as `HH-MM-SS` |
| `hash` | SHA-256 hash of the configured version file |

The expanded result must be a valid PEP 440 version.

## Timestamp versions

Generate a numeric version from the UTC build time:

```toml
[tool.hatch.version.options]
mode = "date"
```

This produces a version such as `2026.09.30`.

Time mode produces `HH.MM.SS`:

```toml
[tool.hatch.version.options]
mode = "time"
```

Set `SOURCE_DATE_EPOCH` to an integer Unix timestamp for reproducible builds.

## Updating versions

Hatch can update versions in `regex` and `multi` modes:

```console
hatch version 2.0.0
```

Script, Git, hash, date, and time modes are read-only.

## Optional Nuitka compilation

Install the optional compiler dependency:

```toml
[build-system]
requires = [
    "hatchling>=1.32.4",
    "hatch-versiondetail[nuitka]>=0.2.0",
]
build-backend = "hatchling.build"
```

Enable compilation for wheel builds:

```toml
[tool.hatch.build.targets.wheel.hooks.versiondetail]
compile = true
packages = ["example"]
working-directory = "src"
```

Additional Nuitka arguments can be supplied explicitly:

```toml
nuitka-args = [
    "--enable-plugin=pyside6",
]
```

The hook compiles non-`__init__.py` modules into platform-specific extension modules and marks the wheel as non-pure. Python sources remain in the wheel; this feature provides compilation, not source concealment.

## Development

Install development dependencies:

```console
uv sync --group dev
```

Run tests:

```console
uv run pytest
```

Build the package:

```console
uv build
```

## AI Note

Initial code creation was created without the use of AI.
AI, specifically GPT 5.6 Sol (light) was used for sanity checks, and additional documentation writing.

## License

Licensed under the [MIT License](LICENSE).

Copyright © 2026 Formation Effects.
