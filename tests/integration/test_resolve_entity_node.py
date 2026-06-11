# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the ResolveEntity node using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes.node_library.advanced_node_library import AdvancedNodeLibrary
from griptape_nodes.node_library.library_registry import LibraryMetadata, LibraryRegistry, LibrarySchema
from griptape_nodes_library_openassetio.resolve_entity_node import ResolveEntity
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from griptape_nodes_library_openassetio.trait_catalogue import load_default_catalogue
from openassetio.errors import BatchElementException

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes_library_openassetio.session import ManagerSession
    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


# Entity reference for the test entity defined in
# openassetio.config.bal.resolve.toml.
_ENTITY_REF = "bal:///test/resolve_entity"


@pytest.fixture
def openassetio_bal_library(
    create_and_register_openassetio_library: Callable[[TraitCatalogue], str],
) -> str:
    """Register a library with the real default catalogue for BAL tests."""
    return create_and_register_openassetio_library(load_default_catalogue())


@pytest.mark.usefixtures("griptape_nodes", "openassetio_resolve_config_env")
class TestResolveEntityNode:
    """Integration tests exercising ResolveEntity against the BAL manager."""

    @pytest.fixture
    def session(self) -> ManagerSession:
        """Create a real BAL-backed session."""
        session_node = OpenAssetIOSession(name="session")
        session_node.process()
        return session_node.parameter_output_values["session"]

    @pytest.fixture
    def node(self, openassetio_bal_library: str, session: ManagerSession) -> ResolveEntity:
        """Create a ResolveEntity node wired to a real session."""
        node = ResolveEntity(name="test_resolve", metadata={"library": openassetio_bal_library})
        node.parameter_values["session"] = session
        return node

    def test_resolved_properties_have_correct_values(self, node: ResolveEntity) -> None:
        """Trait properties populated by BAL appear as output values."""
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["trait_ids"] = [
            "openassetio-mediacreation:content.LocatableContent",
            "openassetio-mediacreation:threeDimensional.Spatial",
        ]

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["openassetio-mediacreation:content.LocatableContent.location"]
            == "file:///mnt/assets/test/resolve_entity.exr"
        )
        assert (
            node.parameter_output_values["openassetio-mediacreation:content.LocatableContent.mimeType"] == "image/x-exr"
        )
        assert node.parameter_output_values["openassetio-mediacreation:threeDimensional.Spatial.upAxis"] == "y"
        assert node.parameter_output_values[
            "openassetio-mediacreation:threeDimensional.Spatial.metersPerUnit"
        ] == pytest.approx(0.01)

    def test_unpopulated_property_is_none(self, node: ResolveEntity) -> None:
        """Trait properties not set by the manager resolve to None.

        The BAL config for this entity omits ``handedness`` from the Spatial trait, so
        its output parameter should remain None.
        """
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["trait_ids"] = [
            "openassetio-mediacreation:threeDimensional.Spatial",
        ]

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values.get("openassetio-mediacreation:threeDimensional.Spatial.handedness") is None

    def test_success_status_is_set(self, node: ResolveEntity) -> None:
        """Successful resolution sets the execution status."""
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["trait_ids"] = [
            "openassetio-mediacreation:content.LocatableContent",
        ]

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == f"SUCCESS: Resolved {_ENTITY_REF}"

    def test_unknown_entity_reports_failure(self, node: ResolveEntity) -> None:
        """Resolving a non-existent entity sets failure status."""
        node.parameter_values["entity_reference"] = "bal:///does/not/exist"
        node.parameter_values["trait_ids"] = [
            "openassetio-mediacreation:content.LocatableContent",
        ]

        with pytest.raises(BatchElementException, match="not found"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityDynamicModuleLoading:
    """Test that catalogue lookup works when the engine loads LibraryHooks from a dynamic module.

    The engine's ``_load_module_from_file()`` uses
    ``importlib.util.spec_from_file_location`` with a generated module name
    (``gtn_dynamic_module_*``), so the ``LibraryHooks`` class it instantiates has a
    different identity to the one imported normally by ``resolve_entity_node.py``. We
    simulate this by creating a fresh ``AdvancedNodeLibrary`` subclass at runtime — same
    interface, different ``type()`` identity.
    """

    def test_catalogue_lookup_with_dynamic_hooks_class(self) -> None:
        """Node construction must succeed even when the hooks class differs."""
        catalogue = load_default_catalogue()

        # Build a class that mirrors LibraryHooks but is a distinct type.
        DynamicLibraryHooks = type(  # noqa: N806
            "LibraryHooks",
            (AdvancedNodeLibrary,),
            {
                "_trait_catalogue": None,
                "trait_catalogue": property(lambda self: self._trait_catalogue),
            },
        )
        hooks = DynamicLibraryHooks()
        hooks._trait_catalogue = catalogue  # type: ignore[attr-defined]  # noqa: SLF001

        library_data = LibrarySchema(
            name="openassetio-dynamic-test",
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

        try:
            node = ResolveEntity(
                name="dyn_test",
                metadata={"library": "openassetio-dynamic-test"},
            )
            assert node._trait_catalogue is catalogue  # noqa: SLF001
        finally:
            LibraryRegistry.unregister_library("openassetio-dynamic-test")
