# griptape-nodes-library-openassetio

A [Griptape Nodes](https://www.griptapenodes.com/) library providing
[OpenAssetIO](https://github.com/OpenAssetIO/OpenAssetIO) integration - drive workflow inputs
(**resolve**) and capture workflow outputs (**publish**) using entity references and the trait
system of any OpenAssetIO-compatible asset management system.

## What is OpenAssetIO?

OpenAssetIO is an open standard that lets host applications talk to arbitrary asset management
systems through a common API. Instead of hard-coding file paths, a workflow refers to assets by
opaque **entity references** (e.g. `myams://shots/sh010/plate`) and asks the configured *manager*
to:

- **Resolve** - translate a reference into concrete data (file locations, metadata, etc.),
  described by a **trait set** (e.g. `openassetio-mediacreation:content.LocatableContent`).
- **Publish** - accept new data from the host and record it in the asset management system,
  returning the final entity reference.
- **Relate** - query references that are related to a source reference, filtered by type of
  relationship and other predicates (e.g. listing asset versions).

This library exposes those operations as Griptape Nodes, so workflows can consume from and
contribute to any pipeline that speaks OpenAssetIO.

## Prerequisites

- [Griptape Nodes engine](https://github.com/griptape-ai/griptape-nodes).
- Python 3.12+.
- An OpenAssetIO manager plugin (e.g. see
  [known examples](https://github.com/OpenAssetIO/OpenAssetIO/blob/main/examples/README.md)).

## Configuration

The library reads two environment variables recognised by OpenAssetIO itself, plus one for
extending the bundled trait catalogue:

| Variable                                 | Purpose                                                                                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `OPENASSETIO_DEFAULT_CONFIG`             | Path to a TOML config selecting the manager and its settings. If unset, the `OpenAssetIOSession` node will report a failure.             |
| `OPENASSETIO_PLUGIN_PATH`                | Optional extra search paths for manager plugins that cannot use Python `importlib` entry points (typically C++ plugins).                 |
| `OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS` | Optional `os.pathsep`-separated list of extra `traits.yml` files to merge into the bundled catalogue. Later files override earlier ones. |

Minimal example config selecting the
[AYON](https://github.com/ynput/ayon-openassetio-manager-plugin) manager:

```toml
[manager]
identifier = "io.ynput.ayon.openassetio.manager"

[manager.settings]
AYON_SERVER_URL = "http://ayon.example.com"
AYON_BUNDLE_NAME = "2026-04-16"
AYON_API_KEY = "<your API key>"
```

Point `OPENASSETIO_DEFAULT_CONFIG` at this file before starting the Griptape Nodes engine. See
[`.env.example`](.env.example) for a template.

The library ships with the
[openassetio-mediacreation](https://github.com/OpenAssetIO/OpenAssetIO-MediaCreation) trait
catalogue built in - additional YAML-formatted trait definitions can be layered on via
`OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS`, provided each file validates against the
[OpenAssetIO-TraitGen Schema](https://github.com/OpenAssetIO/OpenAssetIO-TraitGen/blob/main/python/openassetio_traitgen/schema.json).

## Nodes

All nodes live under the **OpenAssetIO** category in the node picker.

| Node                        | Purpose                                                                                                                                                                             |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **OpenAssetIO Session**     | Bootstraps the OpenAssetIO host, instantiates the configured manager, and emits a session for downstream nodes.                                                                     |
| **Traits**                  | Build, extract, and merge `TraitsData` objects. Pick traits or specifications from the catalogue and expose their properties as parameters.                                         |
| **Is Entity Reference**     | Test whether a string is a valid entity reference for the connected manager.                                                                                                        |
| **Resolve Entity**          | Resolve an entity reference into `TraitsData` populated with the requested trait properties. Supports read and publish (e.g. target file path) metadata.                            |
| **File URL Path Converter** | Cross-platform conversion between file paths and `file://` URLs (System / POSIX / Windows), using OpenAssetIO's built-in converter.                                                 |
| **Preflight Entity**        | First step of publishing - notify the manager that data is about to be written, and receive a *working reference*.                                                                  |
| **Register Entity**         | Second step of publishing - commit the populated `TraitsData` against the working reference and receive the final entity reference.                                                 |
| **Related Entities**        | Query entities related to a source reference via the manager's relationship API, filtered by relationship traits and (optionally) result-entity traits.                             |
| **Create Child Context**    | Create an isolated child context, optionally merging traits into its locale, logically grouping downstream operations and providing session-level metadata (e.g. task, shot, auth). |

### Typical resolve flow

`Resolve Entity` populates an upstream `TraitsData` (describing what you want) with values returned
by the manager:

1. **OpenAssetIO Session** - connect to the configured manager.
2. **Traits** - declare the trait set of interest (the "what you want").
3. **Resolve Entity** - resolve the reference against the manager.
4. **Traits** - extract individual property values as typed outputs for downstream nodes.

### Typical publish flow

Publishing in OpenAssetIO is a two-step handshake with the manager. `TraitsData` flows through the
graph and is enriched at each stage:

1. **Traits** - declare the trait set of the entity to be published, plus any properties known up
   front.
2. **Preflight Entity** - hand the traits to the manager, receive a working reference.
3. **Resolve Entity** *(optional)* - retrieve manager-driven properties (e.g. where to write the
   file, required format).
4. **Traits** *(optional)* - fill in properties derived from elsewhere in the graph.
5. **Register Entity** - commit; receive the final entity reference.

The working reference from Preflight is expected to be threaded straight through any intermediate
nodes to Register.

## Development

Requires [uv](https://docs.astral.sh/uv/).

Many useful commands are wrapped in a `Makefile` for convenience, but you can also invoke tools
directly via `uv run` if you prefer. See the [Makefile](Makefile) for tool usage, or run `make`
with no arguments to see all available targets.

### Quick start

Get set up

```bash
make install          # create .venv and install all deps
make install/hooks    # install pre-commit hooks into .git
```

Run checks

```bash
make check            # lint check code and docs
make format           # auto-format code, docstrings, and markdown
make test/coverage    # pytest with branch coverage
```

### Tooling

Keeping coding agents honest, we have:

- `pytest` for testing.
- `slipcover` for test coverage metrics.
- `ruff` for linting and formatting source code.
- `pyright` for static type checking source code.
- `pydoclint` for docstring linting.
- `docstrfmt` for formatting docstrings.
- `mdformat` for formatting markdown files.
- `gitlint` for commit message linting.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the release process and CI details.

## License

Apache-2.0 - see [LICENSE](LICENSE).
