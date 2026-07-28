# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the ResolveEntity node using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes_library_openassetio.resolve_entity_node import ResolveEntity
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from griptape_nodes_library_openassetio.trait_catalogue import load_default_catalogue
from openassetio.errors import BatchElementException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes.exe_types.node_types import BaseNode
    from griptape_nodes.node_library.library_registry import NodeMetadata
    from griptape_nodes_library_openassetio.session import ManagerSession
    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


# Entity reference for the test entity defined in
# openassetio.config.bal.resolve.toml.
_ENTITY_REF = "bal:///test/resolve_entity"


@pytest.fixture
def openassetio_bal_library(
    create_and_register_openassetio_library: Callable[
        [TraitCatalogue, tuple[tuple[type[BaseNode], NodeMetadata], ...]], str
    ],
) -> str:
    """Register a library with the real default catalogue for BAL tests."""
    return create_and_register_openassetio_library(load_default_catalogue(), ())


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

    def test_resolves_traits_data_with_correct_values(self, node: ResolveEntity) -> None:
        """Resolved TraitsData should contain the property values from BAL."""
        input_td = TraitsData(
            {
                "openassetio-mediacreation:content.LocatableContent",
                "openassetio-mediacreation:threeDimensional.Spatial",
            }
        )
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert (
            output_td.getTraitProperty("openassetio-mediacreation:content.LocatableContent", "location")
            == "file:///mnt/assets/test/resolve_entity.exr"
        )
        assert (
            output_td.getTraitProperty("openassetio-mediacreation:content.LocatableContent", "mimeType")
            == "image/x-exr"
        )
        assert output_td.getTraitProperty("openassetio-mediacreation:threeDimensional.Spatial", "upAxis") == "y"
        assert output_td.getTraitProperty(
            "openassetio-mediacreation:threeDimensional.Spatial", "metersPerUnit"
        ) == pytest.approx(0.01)

    def test_unpopulated_property_is_none(self, node: ResolveEntity) -> None:
        """Trait properties not set by the manager resolve to None.

        The BAL config for this entity omits ``handedness`` from the Spatial trait.
        """
        input_td = TraitsData({"openassetio-mediacreation:threeDimensional.Spatial"})
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        # handedness is not set by BAL, so it should be None.
        assert output_td.getTraitProperty("openassetio-mediacreation:threeDimensional.Spatial", "handedness") is None

    def test_success_status_is_set(self, node: ResolveEntity) -> None:
        """Successful resolution sets the execution status."""
        input_td = TraitsData({"openassetio-mediacreation:content.LocatableContent"})
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == f"SUCCESS: Resolved {_ENTITY_REF}"

    def test_unknown_entity_reports_failure(self, node: ResolveEntity) -> None:
        """Resolving a non-existent entity sets failure status."""
        input_td = TraitsData({"openassetio-mediacreation:content.LocatableContent"})
        node.parameter_values["entity_reference"] = "bal:///does/not/exist"
        node.parameter_values["traits_data_in"] = input_td

        with pytest.raises(BatchElementException, match="not found"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001

    def test_passes_through_session(self, node: ResolveEntity, session: ManagerSession) -> None:
        """Session should be passed through to the output."""
        input_td = TraitsData({"openassetio-mediacreation:content.LocatableContent"})
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        assert node.parameter_output_values["session"] is session

    def test_passes_through_entity_reference(self, node: ResolveEntity) -> None:
        """Entity reference should be passed through to the output."""
        input_td = TraitsData({"openassetio-mediacreation:content.LocatableContent"})
        node.parameter_values["entity_reference"] = _ENTITY_REF
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        assert node.parameter_output_values["entity_reference"] == _ENTITY_REF
