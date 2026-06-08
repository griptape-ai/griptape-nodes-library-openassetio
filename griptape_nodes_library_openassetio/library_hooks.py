# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""AdvancedNodeLibrary hooks for library-level initialisation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from griptape_nodes.node_library.advanced_node_library import AdvancedNodeLibrary

from griptape_nodes_library_openassetio.trait_catalogue import load_default_catalogue

if TYPE_CHECKING:
    from griptape_nodes.node_library.library_registry import Library, LibrarySchema

    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


class LibraryHooks(AdvancedNodeLibrary):
    """Build the shared :class:`TraitCatalogue` once at library load time.

    The engine creates this instance, calls :meth:`before_library_nodes_loaded`, and
    stores it on the ``Library`` object. Nodes retrieve it at construction time via
    ``LibraryRegistry.get_library(name).get_advanced_library().catalogue``.
    """

    def __init__(self) -> None:
        """Initialise with no catalogue (populated by the lifecycle hook)."""
        self._catalogue: TraitCatalogue | None = None

    @property
    def catalogue(self) -> TraitCatalogue:
        """Return the shared trait catalogue.

        :returns: The shared :class:`TraitCatalogue` instance.

        :raises RuntimeError: If the catalogue has not been initialised yet (i.e.
            :meth:`before_library_nodes_loaded` has not been called).
        """
        if self._catalogue is None:
            msg = "Trait catalogue not initialised. LibraryHooks.before_library_nodes_loaded() has not been called."
            raise RuntimeError(msg)
        return self._catalogue

    def before_library_nodes_loaded(self, library_data: LibrarySchema, library: Library) -> None:  # noqa: ARG002
        """Build the trait catalogue before any node classes are imported.

        :param library_data: The library schema (unused, required by interface).
        :param library: The library instance (unused, required by interface).
        """
        self._catalogue = load_default_catalogue()
