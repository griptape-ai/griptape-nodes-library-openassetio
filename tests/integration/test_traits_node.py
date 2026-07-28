# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the Traits node.

These tests exercise the Traits node with a real library registry and
ParameterTransitionComponent, covering code paths that unit tests cannot reach because
they mock the transition component and ``_get_trait_catalogue``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.node_library.library_registry import NodeMetadata
from griptape_nodes.retained_mode.events.context_events import EnsureWorkflowAndFlowRequest
from griptape_nodes.retained_mode.events.node_events import CreateNodeRequest, CreateNodeResultSuccess
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes
from griptape_nodes_library_openassetio.traits_node import Traits
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes.exe_types.node_types import BaseNode
    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue

_NODE_METADATA = NodeMetadata(
    category="OpenAssetIO",
    description="Build and mutate OpenAssetIO TraitsData",
    display_name="Traits",
)


@pytest.fixture
def openassetio_library(
    create_and_register_openassetio_library: Callable[
        [TraitCatalogue, tuple[tuple[type[BaseNode], NodeMetadata], ...]], str
    ],
    stub_trait_catalogue: TraitCatalogue,
) -> str:
    """Register a library with the stub catalogue and Traits node type."""
    return create_and_register_openassetio_library(
        stub_trait_catalogue,
        ((Traits, _NODE_METADATA),),
    )


@pytest.fixture
def _engine_context(griptape_nodes: GriptapeNodes) -> None:
    """Bootstrap a workflow + flow context for node creation via the engine."""
    GriptapeNodes.handle_request(EnsureWorkflowAndFlowRequest())


def _create_traits_node(library_name: str) -> Traits:
    """Create a Traits node through the engine's CreateNodeRequest.

    This registers the node in ObjectManager and NodeManager's flow mapping, which is
    required for ``ParameterTransitionComponent`` to add and remove dynamic parameters.

    :param library_name: The registered library name.

    :returns: The created Traits node instance.
    """
    result = GriptapeNodes.handle_request(
        CreateNodeRequest(
            node_type="Traits",
            specific_library_name=library_name,
        )
    )
    assert isinstance(result, CreateNodeResultSuccess)
    obj_mgr = GriptapeNodes.ObjectManager()
    node = obj_mgr.attempt_get_object_by_name_as_type(result.node_name, Traits)
    assert node is not None
    return node


@pytest.mark.usefixtures("griptape_nodes")
class TestTraitsLibraryCatalogue:
    """Tests that the node loads its catalogue from the real library registry."""

    def test_loads_catalogue_from_library_registry(
        self, openassetio_library: str, stub_trait_catalogue: TraitCatalogue
    ) -> None:
        """Creating a node with a library name should look up the catalogue.

        This exercises ``_get_trait_catalogue`` via ``LibraryRegistry.get_library()``.
        """
        node = Traits(name="test_et", metadata={"library": openassetio_library})

        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        choices = param.ui_options["multi_options"]["choices"]
        expected_ids = stub_trait_catalogue.choosable_ids_for_usage("entity")
        for trait_id in expected_ids:
            assert trait_id in choices


@pytest.mark.usefixtures("_engine_context")
class TestTraitsDynamicParameters:
    """Tests for dynamic parameter creation and removal via the real transition component."""

    @pytest.fixture
    def node(self, openassetio_library: str) -> Traits:
        """Create a Traits node through the engine.

        The engine's ``CreateNodeRequest`` registers the node in both ``ObjectManager``
        and ``NodeManager``'s flow mapping. This is required because
        ``ParameterTransitionComponent`` dispatches ``AddParameterToNodeRequest`` and
        ``RemoveParameterFromNodeRequest`` via the event manager, which looks up the
        node by name.
        """
        return _create_traits_node(openassetio_library)

    # -- Parameter creation --

    def test_selecting_trait_creates_dynamic_parameters(self, node: Traits) -> None:
        """Selecting a trait should create parameters for each property."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        mime_param = node.get_parameter_by_name("test:content.LocatableContent.mimeType")
        assert location_param is not None
        assert mime_param is not None

    def test_dynamic_parameters_are_user_defined(self, node: Traits) -> None:
        """Dynamic parameters must be marked user_defined for save/load."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        assert location_param.user_defined is True

    def test_dynamic_parameters_have_input_and_output_modes(self, node: Traits) -> None:
        """Dynamic parameters should support both INPUT and OUTPUT modes."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        assert location_param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_dynamic_parameters_have_info_badges(self, node: Traits) -> None:
        """Dynamic parameters should have info badges with their tooltip text."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        badge = location_param.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        # The badge message is the property description from the catalogue.
        assert badge.message == "The location"

    # -- Group hierarchy --

    def test_selecting_trait_creates_group_hierarchy(self, node: Traits) -> None:
        """Selecting a trait should create package > namespace > member groups."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        pkg_group = node.get_group_by_name_or_element_id("test")
        ns_group = node.get_group_by_name_or_element_id("test:content")
        member_group = node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert pkg_group is not None
        assert ns_group is not None
        assert member_group is not None

    def test_group_hierarchy_is_nested(self, node: Traits) -> None:
        """Namespace group should be a child of package, member of namespace."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        pkg_group = node.get_group_by_name_or_element_id("test")
        ns_group = node.get_group_by_name_or_element_id("test:content")
        member_group = node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert pkg_group is not None
        assert ns_group is not None
        assert member_group is not None
        assert ns_group in pkg_group.children
        assert member_group in ns_group.children

    # -- Deselection --

    def test_deselecting_all_traits_removes_all_groups(self, node: Traits) -> None:
        """Setting trait_ids to [] should remove all dynamic groups."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        assert node.get_group_by_name_or_element_id("test") is not None

        node.set_parameter_value("trait_ids", [])

        assert node.get_group_by_name_or_element_id("test") is None
        assert node.get_group_by_name_or_element_id("test:content") is None
        assert node.get_group_by_name_or_element_id("test:content.LocatableContent") is None

    def test_deselecting_all_traits_removes_dynamic_parameters(self, node: Traits) -> None:
        """Setting trait_ids to [] should remove all dynamic parameters."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None

        node.set_parameter_value("trait_ids", [])

        assert node.get_parameter_by_name("test:content.LocatableContent.location") is None

    def test_partial_deselection_prunes_empty_groups(self, node: Traits) -> None:
        """Deselecting one namespace should prune only its groups."""
        # Select traits from two namespaces under the same package.
        node.set_parameter_value(
            "trait_ids",
            ["test:content.LocatableContent", "test:identity.DisplayName"],
        )
        assert node.get_group_by_name_or_element_id("test:content") is not None
        assert node.get_group_by_name_or_element_id("test:identity") is not None

        # Deselect identity, keep content.
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        # Package group should remain (it still has content descendants).
        assert node.get_group_by_name_or_element_id("test") is not None
        # Content groups should remain.
        assert node.get_group_by_name_or_element_id("test:content") is not None
        assert node.get_group_by_name_or_element_id("test:content.LocatableContent") is not None
        # Identity groups should be pruned.
        assert node.get_group_by_name_or_element_id("test:identity") is None
        assert node.get_group_by_name_or_element_id("test:identity.DisplayName") is None

    def test_partial_deselection_preserves_remaining_parameters(self, node: Traits) -> None:
        """After partial deselection, remaining dynamic parameters should still exist."""
        node.set_parameter_value(
            "trait_ids",
            ["test:content.LocatableContent", "test:identity.DisplayName"],
        )

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        # Content parameters remain.
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None
        assert node.get_parameter_by_name("test:content.LocatableContent.mimeType") is not None
        # Identity parameter removed.
        assert node.get_parameter_by_name("test:identity.DisplayName.name") is None


@pytest.mark.usefixtures("_engine_context")
class TestTraitsProcessIntegration:
    """Tests for process() using the real catalogue and transition component."""

    @pytest.fixture
    def node(self, openassetio_library: str) -> Traits:
        """Create a Traits node through the engine."""
        return _create_traits_node(openassetio_library)

    def test_process_builds_traits_data(self, node: Traits) -> None:
        """process() should build a TraitsData with the selected traits."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert "test:content.LocatableContent" in output_td.traitSet()

    def test_process_applies_override_values(self, node: Traits) -> None:
        """process() should apply override values to the TraitsData."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.parameter_values["test:content.LocatableContent.location"] = "file:///override.exr"

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert output_td.getTraitProperty("test:content.LocatableContent", "location") == "file:///override.exr"

    def test_process_outputs_property_values_to_ports(self, node: Traits) -> None:
        """process() should write final values to the dynamic output ports."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.parameter_values["test:content.LocatableContent.location"] = "file:///test.exr"

        node.process()

        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///test.exr"

    def test_process_outputs_trait_ids(self, node: Traits) -> None:
        """process() should write all trait IDs to output_trait_ids."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        node.process()

        output_ids = node.parameter_values.get("output_trait_ids", "")
        assert "test:content.LocatableContent" in output_ids

    def test_process_expands_specification(self, node: Traits) -> None:
        """process() should expand specification IDs to their constituent traits."""
        node.set_parameter_value("trait_ids", ["test:specification:content.NamedContent"])

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert "test:content.LocatableContent" in output_td.traitSet()
        assert "test:identity.DisplayName" in output_td.traitSet()

    def test_process_specification_applies_overrides(self, node: Traits) -> None:
        """process() should apply overrides to properties from expanded specifications."""
        node.set_parameter_value("trait_ids", ["test:specification:content.NamedContent"])
        node.parameter_values["test:content.LocatableContent.location"] = "file:///spec.exr"

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert output_td.getTraitProperty("test:content.LocatableContent", "location") == "file:///spec.exr"
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///spec.exr"

    def test_process_merges_upstream_traits_data(self, node: Traits) -> None:
        """process() should merge upstream TraitsData values as pass-through."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        upstream_td = TraitsData({"test:content.LocatableContent"})
        upstream_td.setTraitProperty("test:content.LocatableContent", "location", "file:///upstream.exr")
        node.parameter_values["traits_data_in"] = upstream_td

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert output_td.getTraitProperty("test:content.LocatableContent", "location") == "file:///upstream.exr"
        # The upstream value should pass through to the output port.
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///upstream.exr"

    def test_process_override_takes_priority_over_upstream(self, node: Traits) -> None:
        """process() override values should take priority over upstream."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        upstream_td = TraitsData({"test:content.LocatableContent"})
        upstream_td.setTraitProperty("test:content.LocatableContent", "location", "file:///upstream.exr")
        node.parameter_values["traits_data_in"] = upstream_td
        node.parameter_values["test:content.LocatableContent.location"] = "file:///override.exr"

        node.process()

        output_td = node.parameter_output_values["traits_data_out"]
        assert isinstance(output_td, TraitsData)
        assert output_td.getTraitProperty("test:content.LocatableContent", "location") == "file:///override.exr"
