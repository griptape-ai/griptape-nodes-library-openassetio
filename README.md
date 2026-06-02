# griptape-nodes-library-openassetio

A [Griptape Nodes](https://www.griptapenodes.com/) library providing
[OpenAssetIO](https://github.com/OpenAssetIO/OpenAssetIO) integration - resolve/publish asset
metadata between Griptape Nodes and any OpenAssetIO-compatible asset management system.

## Prerequisites

- Griptape Nodes engine v0.85.3+.
- An OpenAssetIO manager plugin configured via `OPENASSETIO_DEFAULT_CONFIG`.

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

## License

Apache-2.0 — see `LICENSE`.
