# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""BAL fixtures for integration tests."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from griptape_nodes.node_library.library_registry import LibraryMetadata, LibraryRegistry, LibrarySchema
from griptape_nodes_library_openassetio.library_hooks import LibraryHooks

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"


@pytest.fixture
def bal_minimal_config() -> str:
    """Return the path to the minimal BAL config file."""
    return str(_RESOURCES / "openassetio.config.bal.minimal.toml")


@pytest.fixture
def bal_resolve_config() -> str:
    """Return the path to the resolve-test BAL config file."""
    return str(_RESOURCES / "openassetio.config.bal.resolve.toml")


@pytest.fixture
def openassetio_resolve_config_env(
    monkeypatch: pytest.MonkeyPatch,
    bal_resolve_config: str,
) -> str:
    """Set ``OPENASSETIO_DEFAULT_CONFIG`` to the resolve-test BAL config.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param bal_resolve_config: Path to the resolve-test BAL config.

    :returns: The config file path that was set.
    """
    monkeypatch.setenv("OPENASSETIO_DEFAULT_CONFIG", bal_resolve_config)
    return bal_resolve_config


@pytest.fixture
def openassetio_minimal_config_env(
    monkeypatch: pytest.MonkeyPatch,
    bal_minimal_config: str,
) -> str:
    """Set ``OPENASSETIO_DEFAULT_CONFIG`` to the BAL minimal config.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param bal_minimal_config: Path to the minimal BAL config.

    :returns: The config file path that was set.
    """
    monkeypatch.setenv("OPENASSETIO_DEFAULT_CONFIG", bal_minimal_config)
    return bal_minimal_config


@pytest.fixture
def create_and_register_openassetio_library() -> Iterator[Callable[[TraitCatalogue], str]]:
    """Create and register a library with a given :class:`TraitCatalogue`.

    Each call creates a uniquely-named library in the :class:`LibraryRegistry` with a
    :class:`LibraryHooks` instance holding the supplied catalogue. All registered
    libraries are unregistered on teardown.

    :returns: A callable that accepts a :class:`TraitCatalogue` and returns the
        registered library name.
    """
    registered: list[str] = []

    def _create(catalogue: TraitCatalogue) -> str:
        name = f"openassetio-test-{uuid.uuid4().hex[:8]}"

        hooks = LibraryHooks()
        hooks._trait_catalogue = catalogue  # noqa: SLF001

        library_data = LibrarySchema(
            name=name,
            library_schema_version="0.5.0",
            metadata=LibraryMetadata(
                author="test",
                description="test",
                library_version="0.0.0",
                engine_version="0.0.0",
                tags=[],
            ),
            categories=[],
            nodes=[],
        )
        LibraryRegistry.generate_new_library(library_data, advanced_library=hooks)
        registered.append(name)
        return name

    yield _create

    for name in registered:
        LibraryRegistry.unregister_library(name)
