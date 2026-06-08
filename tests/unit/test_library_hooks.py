# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the LibraryHooks AdvancedNodeLibrary subclass."""

from __future__ import annotations

from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.library_hooks as hooks_mod
import pytest
from griptape_nodes.node_library.library_registry import Library, LibrarySchema
from griptape_nodes_library_openassetio.library_hooks import LibraryHooks
from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue, load_default_catalogue


class TestLibraryHooks:
    """Tests for LibraryHooks lifecycle and catalogue access."""

    def test_catalogue_raises_before_hook_called(self) -> None:
        """Accessing catalogue before before_library_nodes_loaded raises RuntimeError."""
        hooks = LibraryHooks()

        with pytest.raises(RuntimeError, match="Trait catalogue not initialised"):
            _ = hooks.catalogue

    def test_before_library_nodes_loaded_populates_catalogue(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Calling before_library_nodes_loaded should build and store the catalogue."""
        sentinel_catalogue = Mock(spec=TraitCatalogue)
        mock_load = create_autospec(load_default_catalogue, return_value=sentinel_catalogue)
        monkeypatch.setattr(hooks_mod, "load_default_catalogue", mock_load)

        hooks = LibraryHooks()
        hooks.before_library_nodes_loaded(
            library_data=Mock(spec=LibrarySchema),
            library=Mock(spec=Library),
        )

        mock_load.assert_called_once_with()
        assert hooks.catalogue is sentinel_catalogue

    def test_catalogue_returns_same_instance_on_repeated_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The catalogue property should return the same instance every time."""
        sentinel_catalogue = Mock(spec=TraitCatalogue)
        monkeypatch.setattr(
            hooks_mod,
            "load_default_catalogue",
            create_autospec(load_default_catalogue, return_value=sentinel_catalogue),
        )

        hooks = LibraryHooks()
        hooks.before_library_nodes_loaded(
            library_data=Mock(spec=LibrarySchema),
            library=Mock(spec=Library),
        )

        assert hooks.catalogue is hooks.catalogue
