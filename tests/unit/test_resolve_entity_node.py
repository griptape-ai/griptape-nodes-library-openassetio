# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the ResolveEntity node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.resolve_entity_node as resolve_node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterGroup, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from griptape_nodes_library_openassetio.resolve_entity_node import ResolveEntity
from griptape_nodes_library_openassetio.session import ManagerSession
from openassetio import Context
from openassetio.hostApi import HostInterface, Manager

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


@pytest.fixture
def _mock_trait_catalogue(monkeypatch: pytest.MonkeyPatch, stub_trait_catalogue: TraitCatalogue) -> None:
    """Replace ``_get_trait_catalogue`` so nodes get a test catalogue without the registry."""
    monkeypatch.setattr(resolve_node_mod, "_get_trait_catalogue", lambda _metadata: stub_trait_catalogue)


def _make_session() -> ManagerSession:
    """Build a mock ManagerSession."""
    return ManagerSession(
        manager=Mock(spec=Manager),
        context=Mock(spec=Context),
        host_interface=Mock(spec=HostInterface),
    )


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestResolveEntityStructure:
    """Tests for the ResolveEntity node parameter structure."""

    @pytest.fixture
    def node(self) -> ResolveEntity:
        return ResolveEntity(name="test_resolve")

    def test_is_success_failure_node(self, node: ResolveEntity) -> None:
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_input_parameter(self, node: ResolveEntity) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_session_parameter_is_not_serializable(self, node: ResolveEntity) -> None:
        """ManagerSession is not JSON-serializable, so the parameter must opt out."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_parameter(self, node: ResolveEntity) -> None:
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_has_trait_ids_parameter(self, node: ResolveEntity) -> None:
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_trait_ids_has_multi_options(self, node: ResolveEntity) -> None:
        """trait_ids should have a MultiOptions trait with the catalogue's trait IDs."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        ui_opts = param.ui_options
        assert "multi_options" in ui_opts
        assert ui_opts["multi_options"]["show_search"] is True
        assert ui_opts["multi_options"]["allow_user_created_options"] is False
        choices = ui_opts["multi_options"]["choices"]
        assert "test:content.LocatableContent" in choices
        assert "test:identity.DisplayName" in choices

    def test_trait_ids_choices_include_specifications(self, node: ResolveEntity) -> None:
        """Specifications should appear in the MultiOptions choices."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        choices = param.ui_options["multi_options"]["choices"]
        assert "test:specification:content.NamedContent" in choices

    def test_default_metadata(self, node: ResolveEntity) -> None:
        assert node.metadata["category"] == "OpenAssetIO"


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityCatalogueLookup:
    """Tests for the catalogue lookup via _get_trait_catalogue."""

    def test_constructs_without_library_metadata(self) -> None:
        """Constructing without metadata['library'] should succeed with empty catalogue.

        The engine constructs bare reference nodes during serialization via
        ``type(node)(name="REFERENCE NODE")`` — no metadata['library'] is present. The
        node must tolerate this gracefully by using an empty catalogue.
        """
        node = ResolveEntity(name="no_library")
        assert len(node._trait_catalogue.all_choosable_ids()) == 0  # noqa: SLF001
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        assert param.ui_options["multi_options"]["choices"] == []


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestResolveEntityDynamicParameters:
    """Unit tests for dynamic parameter logic with mocked transition component.

    These tests verify the logic of ``_build_desired_params``,
    ``_ensure_trait_groups_exist``, and ``_remove_stale_groups`` without dispatching
    engine events. The transition component is mocked so no engine registration is
    needed.
    """

    @pytest.fixture
    def node(self) -> ResolveEntity:
        """Create a node with a mocked transition component."""
        node = ResolveEntity(name="test_resolve_dyn")
        # Mock the transition component so we don't need engine registration.
        node._transition_component = create_autospec(node._transition_component)  # noqa: SLF001
        return node

    def test_build_desired_params_returns_correct_descriptors(self, node: ResolveEntity) -> None:
        """_build_desired_params should return TransitionParameter for each property."""
        params = node._build_desired_params(["test:content.LocatableContent"])  # noqa: SLF001

        names = [p.name for p in params]
        assert "test:content.LocatableContent.location" in names
        assert "test:content.LocatableContent.mimeType" in names

        location = next(p for p in params if p.name == "test:content.LocatableContent.location")
        assert location.output_type == "str"
        assert location.allowed_modes == frozenset({ParameterMode.OUTPUT})
        assert location.input_types == frozenset()

    def test_build_desired_params_maps_property_types(self, node: ResolveEntity) -> None:
        """Property types (integer, float, boolean) should map to Griptape types."""
        params = node._build_desired_params(["test:types.Mixed"])  # noqa: SLF001

        by_name = {p.name: p for p in params}
        assert by_name["test:types.Mixed.count"].output_type == "int"
        assert by_name["test:types.Mixed.ratio"].output_type == "float"
        assert by_name["test:types.Mixed.enabled"].output_type == "bool"

    def test_build_desired_params_skips_unknown_trait_ids(self, node: ResolveEntity) -> None:
        """Unknown trait IDs should be silently skipped."""
        params = node._build_desired_params(["unknown:trait.Id"])  # noqa: SLF001
        assert params == []

    def test_ensure_trait_groups_creates_hierarchy(self, node: ResolveEntity) -> None:
        """_ensure_trait_groups_exist should create package > namespace > member groups."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        pkg = node.get_group_by_name_or_element_id("test")
        assert pkg is not None
        assert pkg.ui_options.get("display_name") == "test"

        ns = node.get_group_by_name_or_element_id("test:content")
        assert ns is not None
        assert ns.parent_group_name == "test"
        assert ns.ui_options.get("display_name") == "content"

        member = node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert member is not None
        assert member.parent_group_name == "test:content"
        assert member.ui_options.get("display_name") == "LocatableContent"

    def test_ensure_trait_groups_is_idempotent(self, node: ResolveEntity) -> None:
        """Calling _ensure_trait_groups_exist twice should not duplicate groups."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001
        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        # Should still have exactly one of each.
        all_groups = node.root_ui_element.find_elements_by_type(ParameterGroup)
        names = [g.name for g in all_groups if g.user_defined]
        assert names.count("test") == 1
        assert names.count("test:content") == 1
        assert names.count("test:content.LocatableContent") == 1

    def test_ensure_trait_groups_shares_package_across_namespaces(self, node: ResolveEntity) -> None:
        """Two traits in the same package should share the package group."""
        catalogue = node._trait_catalogue  # noqa: SLF001
        defn_content = catalogue.get_trait("test:content.LocatableContent")
        defn_identity = catalogue.get_trait("test:identity.DisplayName")
        assert defn_content is not None
        assert defn_identity is not None

        node._ensure_trait_groups_exist(defn_content)  # noqa: SLF001
        node._ensure_trait_groups_exist(defn_identity)  # noqa: SLF001

        content_ns = node.get_group_by_name_or_element_id("test:content")
        identity_ns = node.get_group_by_name_or_element_id("test:identity")
        assert content_ns is not None
        assert identity_ns is not None
        # Both under the same package group.
        assert content_ns.parent_group_name == "test"
        assert identity_ns.parent_group_name == "test"

    def test_v2_trait_member_group_display_name(self, node: ResolveEntity) -> None:
        """v2+ traits should have display name 'MemberName (v2)' on member group."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent.v2")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        member = node.get_group_by_name_or_element_id("test:content.LocatableContent.v2")
        assert member is not None
        assert member.ui_options.get("display_name") == "LocatableContent (v2)"

    def test_package_group_has_badge(self, node: ResolveEntity) -> None:
        """Package group should have an info badge with the package description."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        pkg = node.get_group_by_name_or_element_id("test")
        assert pkg is not None
        badge = pkg.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Test package description"

    def test_namespace_group_has_badge(self, node: ResolveEntity) -> None:
        """Namespace group should have an info badge with the namespace description."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        ns = node.get_group_by_name_or_element_id("test:content")
        assert ns is not None
        badge = ns.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Content namespace description"

    def test_member_group_has_badge(self, node: ResolveEntity) -> None:
        """Member group should have an info badge with the trait description."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        member = node.get_group_by_name_or_element_id("test:content.LocatableContent")
        assert member is not None
        badge = member.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Locatable content trait"

    def test_remove_stale_groups_prunes_empty_package(self, node: ResolveEntity) -> None:
        """Package groups with no Parameter descendants should be removed."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None
        # Create groups but don't add any parameters (transition is mocked).
        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        assert node.get_group_by_name_or_element_id("test") is not None

        node._remove_stale_groups()  # noqa: SLF001

        # All groups removed since there are no parameters inside.
        assert node.get_group_by_name_or_element_id("test") is None
        assert node.get_group_by_name_or_element_id("test:content") is None
        assert node.get_group_by_name_or_element_id("test:content.LocatableContent") is None

    def test_after_value_set_calls_rebuild(self, node: ResolveEntity) -> None:
        """Setting trait_ids should trigger _rebuild_dynamic_outputs."""
        rebuild_mock = create_autospec(node._rebuild_dynamic_outputs)  # noqa: SLF001
        node._rebuild_dynamic_outputs = rebuild_mock  # noqa: SLF001

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        rebuild_mock.assert_called_once_with(["test:content.LocatableContent"])


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestResolveEntityProcess:
    """Tests for the ResolveEntity process() method."""

    @pytest.fixture
    def node(self) -> ResolveEntity:
        return ResolveEntity(name="test_resolve_proc")

    def test_process_populates_outputs_from_resolve_result(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
    ) -> None:
        """process() should delegate to resolve_entity and populate output parameters."""
        mock_resolve = create_autospec(
            resolve_entity,
            return_value={
                "test:content.LocatableContent.location": "file:///path/to/file.exr",
                "test:content.LocatableContent.mimeType": "image/x-exr",
            },
        )
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///path/to/file.exr"
        assert node.parameter_output_values["test:content.LocatableContent.mimeType"] == "image/x-exr"

    def test_process_delegates_to_resolve_entity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
    ) -> None:
        """process() should call resolve_entity with the correct arguments."""
        mock_resolve = create_autospec(resolve_entity, return_value={})
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        node.process()

        mock_resolve.assert_called_once_with(session, "asset://my/entity", {"test:content.LocatableContent"})

    def test_process_sets_success_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
    ) -> None:
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", create_autospec(resolve_entity, return_value={}))

        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Resolved asset://my/entity"

    def test_process_fails_when_session_missing(self, node: ResolveEntity) -> None:
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        node._handle_failure_exception = mock_handle  # noqa: SLF001

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: No session connected"

    def test_process_fails_when_entity_reference_missing(self, node: ResolveEntity) -> None:
        session = _make_session()
        node.parameter_values["session"] = session
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        node._handle_failure_exception = mock_handle  # noqa: SLF001

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: No entity reference provided"

    def test_process_fails_when_trait_ids_empty(self, node: ResolveEntity) -> None:
        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/entity"

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        node._handle_failure_exception = mock_handle  # noqa: SLF001

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: No trait IDs selected"

    def test_process_clears_stale_outputs_from_previous_run(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
    ) -> None:
        """Output values from a prior resolve must not leak into the next run.

        If the first resolve populates property X but the second resolve does not return
        X, the output for X should be None — not the stale value from the first run.
        """
        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        # First run: both properties populated.
        mock_resolve_1 = create_autospec(
            resolve_entity,
            return_value={
                "test:content.LocatableContent.location": "file:///first.exr",
                "test:content.LocatableContent.mimeType": "image/x-exr",
            },
        )
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve_1)
        node.process()
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///first.exr"
        assert node.parameter_output_values["test:content.LocatableContent.mimeType"] == "image/x-exr"

        # Second run: only location is returned by the manager.
        mock_resolve_2 = create_autospec(
            resolve_entity,
            return_value={
                "test:content.LocatableContent.location": "file:///second.exr",
            },
        )
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve_2)
        node.process()

        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///second.exr"
        # mimeType was not returned in the second resolve — must be None, not the stale value.
        assert node.parameter_output_values.get("test:content.LocatableContent.mimeType") is None

    def test_process_fails_on_resolve_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
    ) -> None:
        monkeypatch.setattr(
            resolve_node_mod,
            "resolve_entity",
            create_autospec(resolve_entity, side_effect=RuntimeError("Entity not found")),
        )

        session = _make_session()
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://missing"
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        with pytest.raises(RuntimeError, match="Entity not found"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Entity not found"
