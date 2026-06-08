# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for ResolveEntity dynamic parameter creation.

These tests exercise the full engine round-trip: setting trait_ids triggers
``_rebuild_dynamic_outputs`` which dispatches ``AddParameterToNodeRequest`` /
``RemoveParameterFromNodeRequest`` events through the engine, verifying that parameters
and groups are correctly created, removed, serialized, and that downstream connections
are preserved.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from griptape_nodes.exe_types.core_types import Parameter, ParameterGroup, ParameterMode
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes.retained_mode.events.connection_events import (
    CreateConnectionRequest,
    CreateConnectionResultSuccess,
)
from griptape_nodes.retained_mode.events.flow_events import (
    CreateFlowRequest,
    CreateFlowResultSuccess,
)
from griptape_nodes.retained_mode.events.parameter_events import (
    AddParameterGroupToNodeRequest,
    AddParameterToNodeRequest,
)
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes
from griptape_nodes_library_openassetio.resolve_entity_node import ResolveEntity
from griptape_nodes_library_openassetio.trait_catalogue import (
    TraitCatalogue,
    TraitDefinition,
    TraitProperty,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes.exe_types.node_types import BaseNode


@pytest.fixture
def openassetio_test_library(
    create_and_register_openassetio_library: Callable[[TraitCatalogue], str],
    stub_trait_catalogue: TraitCatalogue,
) -> str:
    """Register a temporary library with a test TraitCatalogue."""
    return create_and_register_openassetio_library(stub_trait_catalogue)


def _register_node_in_flow(engine: GriptapeNodes, node: BaseNode, flow_name: str) -> None:
    """Register a manually-created node with the engine so events work.

    :param engine: The engine singleton.
    :param node: The node instance to register.
    :param flow_name: The flow to add the node to.
    """
    flow = engine.FlowManager().get_flow_by_name(flow_name)
    flow.add_node(node)
    engine.ObjectManager().add_object_by_name(node.name, node)
    engine.NodeManager()._name_to_parent_flow_name[node.name] = flow_name  # noqa: SLF001


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityDynamicParameters:
    """Integration tests for dynamic parameter creation via the engine."""

    @pytest.fixture
    def engine(self) -> GriptapeNodes:
        """Provide the initialised engine singleton."""
        return GriptapeNodes()

    @pytest.fixture
    def flow_name(self, engine: GriptapeNodes) -> str:
        """Create a workflow and flow for the test."""
        engine.ContextManager().push_workflow("test_wf")
        result = engine.handle_request(
            CreateFlowRequest(parent_flow_name=None, flow_name="test_flow", set_as_new_context=True)
        )
        assert isinstance(result, CreateFlowResultSuccess)
        return result.flow_name

    @pytest.fixture
    def node(self, openassetio_test_library: str, engine: GriptapeNodes, flow_name: str) -> ResolveEntity:
        """Create a ResolveEntity node registered with the engine."""
        node = ResolveEntity(name="resolve", metadata={"library": openassetio_test_library})
        _register_node_in_flow(engine, node, flow_name)
        return node

    def test_selecting_trait_creates_output_parameters(self, node: ResolveEntity) -> None:
        """Selecting a trait ID should create output parameters for its properties."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        assert location_param.output_type == "str"
        assert location_param.allowed_modes == {ParameterMode.OUTPUT}

        mime_param = node.get_parameter_by_name("test:content.LocatableContent.mimeType")
        assert mime_param is not None
        assert mime_param.output_type == "str"

    def test_creates_four_level_group_tree(self, node: ResolveEntity) -> None:
        """Dynamic outputs should be nested: package > namespace > member > property."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        pkg_group = node.get_group_by_name_or_element_id("test")
        assert pkg_group is not None
        assert pkg_group.ui_options.get("display_name") == "test"

        ns_group = node.get_group_by_name_or_element_id("test:content")
        assert ns_group is not None
        assert ns_group.parent_group_name == "test"
        assert ns_group.ui_options.get("display_name") == "content"

        member_group = node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert member_group is not None
        assert member_group.parent_group_name == "test:content"
        assert member_group.ui_options.get("display_name") == "LocatableContent"

        param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert param is not None
        assert param.parent_element_name == "test:content.LocatableContent"
        assert param.display_name == "location"

    def test_v2_trait_gets_version_suffix_in_group_name(self, node: ResolveEntity) -> None:
        """v2+ traits use the full trait ID (with .v2) as the member group name."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent.v2"])

        member_group = node.get_group_by_name_or_element_id("test:content.LocatableContent.v2")
        assert member_group is not None
        assert member_group.parent_group_name == "test:content"
        assert member_group.ui_options.get("display_name") == "LocatableContent (v2)"

        param = node.get_parameter_by_name("test:content.LocatableContent.v2.location")
        assert param is not None
        assert param.parent_element_name == "test:content.LocatableContent.v2"

    def test_same_package_traits_share_package_group(self, node: ResolveEntity) -> None:
        """Two traits in the same package should share the package-level group."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent", "test:identity.DisplayName"])

        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None
        assert node.get_parameter_by_name("test:identity.DisplayName.name") is not None

        pkg_group = node.get_group_by_name_or_element_id("test")
        assert pkg_group is not None
        content_group = node.get_group_by_name_or_element_id("test:content")
        identity_group = node.get_group_by_name_or_element_id("test:identity")
        assert content_group is not None
        assert identity_group is not None
        assert content_group.parent_group_name == "test"
        assert identity_group.parent_group_name == "test"

    def test_property_type_mapping(self, node: ResolveEntity) -> None:
        """Trait property types should map to Griptape parameter types."""
        node.set_parameter_value("trait_ids", ["test:types.Mixed"])

        count = node.get_parameter_by_name("test:types.Mixed.count")
        assert count is not None
        assert count.output_type == "int"

        ratio = node.get_parameter_by_name("test:types.Mixed.ratio")
        assert ratio is not None
        assert ratio.output_type == "float"

        enabled = node.get_parameter_by_name("test:types.Mixed.enabled")
        assert enabled is not None
        assert enabled.output_type == "bool"

    def test_changing_trait_ids_removes_old_parameters(self, node: ResolveEntity) -> None:
        """Switching traits removes the old params and creates new ones."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None

        node.set_parameter_value("trait_ids", ["test:identity.DisplayName"])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is None
        assert node.get_parameter_by_name("test:identity.DisplayName.name") is not None

    def test_changing_trait_ids_removes_stale_namespace_and_member_groups(self, node: ResolveEntity) -> None:
        """Switching traits within the same package removes stale inner groups."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent", "test:identity.DisplayName"])
        assert node.get_group_by_name_or_element_id("test:content") is not None
        assert node.get_group_by_name_or_element_id("test:identity") is not None

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        assert node.get_group_by_name_or_element_id("test") is not None
        assert node.get_group_by_name_or_element_id("test:content") is not None
        assert node.get_group_by_name_or_element_id("test:content.LocatableContent") is not None
        assert node.get_group_by_name_or_element_id("test:identity") is None
        assert node.get_group_by_name_or_element_id("test:identity.DisplayName") is None

    def test_clearing_trait_ids_removes_all_dynamic_parameters(self, node: ResolveEntity) -> None:
        """Clearing trait_ids removes all dynamic params and groups."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None

        node.set_parameter_value("trait_ids", [])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is None
        assert node.get_group_by_name_or_element_id("test") is None

    def test_selecting_specification_expands_to_trait_outputs(self, node: ResolveEntity) -> None:
        """Selecting a specification creates outputs for all its constituent traits."""
        node.set_parameter_value("trait_ids", ["test:specification:content.NamedContent"])

        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None
        assert node.get_parameter_by_name("test:content.LocatableContent.mimeType") is not None
        assert node.get_parameter_by_name("test:identity.DisplayName.name") is not None

    def test_dynamic_parameters_are_user_defined(self, node: ResolveEntity) -> None:
        """Dynamic parameters must be marked user_defined for save/load."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert param is not None
        assert param.user_defined is True

    def test_dynamic_parameters_have_tooltip(self, node: ResolveEntity) -> None:
        """Output parameters carry the trait property description as tooltip."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        assert location_param.tooltip == "The location"

        mime_param = node.get_parameter_by_name("test:content.LocatableContent.mimeType")
        assert mime_param is not None
        assert mime_param.tooltip == "The MIME type"

    def test_name_collision_package_equals_namespace(
        self,
        create_and_register_openassetio_library: Callable[[TraitCatalogue], str],
        engine: GriptapeNodes,
        flow_name: str,
    ) -> None:
        """Package and namespace with the same name produce distinct groups."""
        # Register a separate library with a catalogue crafted to provoke
        # a package/namespace name collision.
        catalogue = TraitCatalogue(
            {
                "content:data.FileRef": TraitDefinition(
                    trait_id="content:data.FileRef",
                    package="content",
                    namespace="data",
                    member_name="FileRef",
                    version="1",
                    description="A file reference",
                    usage=["entity"],
                    properties={
                        "path": TraitProperty(name="path", type="string", description="File path"),
                    },
                ),
                "test:content.Metadata": TraitDefinition(
                    trait_id="test:content.Metadata",
                    package="test",
                    namespace="content",
                    member_name="Metadata",
                    version="1",
                    description="Content metadata",
                    usage=["entity"],
                    properties={
                        "author": TraitProperty(name="author", type="string", description="Author name"),
                    },
                ),
            },
            specifications={},
        )
        library_name = create_and_register_openassetio_library(catalogue)

        node = ResolveEntity(name="collision_node", metadata={"library": library_name})
        _register_node_in_flow(engine, node, flow_name)

        # Bypass MultiOptions validation by calling _rebuild_dynamic_outputs directly.
        node._rebuild_dynamic_outputs(["content:data.FileRef", "test:content.Metadata"])  # noqa: SLF001

        path_param = node.get_parameter_by_name("content:data.FileRef.path")
        assert path_param is not None
        author_param = node.get_parameter_by_name("test:content.Metadata.author")
        assert author_param is not None

        pkg_content = node.get_group_by_name_or_element_id("content")
        assert pkg_content is not None

        pkg_test = node.get_group_by_name_or_element_id("test")
        assert pkg_test is not None

        # "test:content" is the namespace group, distinct from the "content" package.
        ns_content = node.get_group_by_name_or_element_id("test:content")
        assert ns_content is not None
        assert ns_content.parent_group_name == "test"

        ns_data = node.get_group_by_name_or_element_id("content:data")
        assert ns_data is not None
        assert ns_data.parent_group_name == "content"

        assert path_param.parent_element_name == "content:data.FileRef"
        assert author_param.parent_element_name == "test:content.Metadata"

    def test_dynamic_parameters_survive_serialize_roundtrip(
        self, node: ResolveEntity, openassetio_test_library: str, engine: GriptapeNodes, flow_name: str
    ) -> None:
        """Dynamic params and groups survive a serialize → replay cycle."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        assert node.get_parameter_by_name("test:content.LocatableContent.location") is not None

        # Collect user_defined groups (same data the engine serializer uses).
        all_groups = node.root_ui_element.find_elements_by_type(ParameterGroup)
        group_commands = [
            AddParameterGroupToNodeRequest(
                node_name="fresh_node",
                group_name=g.name,
                parent_element_name=g.parent_group_name,
                ui_options=g.ui_options or {},
                is_user_defined=True,
                initial_setup=True,
            )
            for g in all_groups
            if g.user_defined
        ]

        # Collect user_defined parameters.
        param_commands = [
            AddParameterToNodeRequest.create(**{**p.to_dict(), "initial_setup": True, "node_name": "fresh_node"})
            for p in node.parameters
            if p.user_defined
        ]

        # Verify expected structure was captured.
        group_names = [cmd.group_name for cmd in group_commands]
        assert "test" in group_names
        assert "test:content" in group_names
        assert "test:content.LocatableContent" in group_names

        param_names = [cmd.parameter_name for cmd in param_commands]
        assert "test:content.LocatableContent.location" in param_names
        assert "test:content.LocatableContent.mimeType" in param_names

        # Replay on a fresh node.
        fresh_node = ResolveEntity(name="fresh_node", metadata={"library": openassetio_test_library})
        _register_node_in_flow(engine, fresh_node, flow_name)

        assert fresh_node.get_parameter_by_name("test:content.LocatableContent.location") is None

        for cmd in group_commands:
            engine.handle_request(cmd)
        for cmd in param_commands:
            engine.handle_request(cmd)

        # Verify restored state.
        location = fresh_node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location is not None
        assert location.output_type == "str"
        assert location.user_defined is True
        assert location.parent_element_name == "test:content.LocatableContent"

        pkg_group = fresh_node.get_group_by_name_or_element_id("test")
        assert pkg_group is not None
        ns_group = fresh_node.get_group_by_name_or_element_id("test:content")
        assert ns_group is not None
        assert ns_group.parent_group_name == "test"
        member_group = fresh_node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert member_group is not None
        assert member_group.parent_group_name == "test:content"

    def test_dynamic_output_parameters_have_badges(self, node: ResolveEntity) -> None:
        """Dynamic output parameters should have an info badge with the property description."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        location_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert location_param is not None
        badge = location_param.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "The location"

        mime_param = node.get_parameter_by_name("test:content.LocatableContent.mimeType")
        assert mime_param is not None
        badge = mime_param.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "The MIME type"

    def test_connection_survives_rebuild_with_same_trait_ids(
        self,
        engine: GriptapeNodes,
        node: ResolveEntity,
        flow_name: str,
    ) -> None:
        """A connection to a dynamic output must persist when trait_ids is re-set."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        # Create a downstream node and connect to the dynamic output.
        downstream = _DownstreamNode(name="downstream")
        _register_node_in_flow(engine, downstream, flow_name)

        result = engine.handle_request(
            CreateConnectionRequest(
                source_node_name="resolve",
                source_parameter_name="test:content.LocatableContent.location",
                target_node_name="downstream",
                target_parameter_name="location_input",
            )
        )
        assert isinstance(result, CreateConnectionResultSuccess)

        # Verify the connection exists before the rebuild.
        connections = engine.FlowManager().get_connections()
        outgoing = connections.outgoing_index.get("resolve", {})
        assert "test:content.LocatableContent.location" in outgoing

        # Re-set trait_ids to the same value — triggers _rebuild_dynamic_outputs.
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        # The connection must still exist after rebuild.
        connections_after = engine.FlowManager().get_connections()
        outgoing_after = connections_after.outgoing_index.get("resolve", {})
        assert "test:content.LocatableContent.location" in outgoing_after

        # The connection's source_parameter must be the current parameter instance.
        connection_ids = outgoing_after["test:content.LocatableContent.location"]
        assert len(connection_ids) == 1
        connection = connections_after.connections[connection_ids[0]]
        current_param = node.get_parameter_by_name("test:content.LocatableContent.location")
        assert connection.source_parameter is current_param


class _DownstreamNode(DataNode):
    """Minimal downstream node with a string input for connection testing."""

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, metadata=metadata or {})
        self.add_parameter(
            Parameter(
                name="location_input",
                type="str",
                input_types=["str"],
                default_value="",
                tooltip="Receives a string value",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )

    def process(self) -> None:
        """No-op."""
