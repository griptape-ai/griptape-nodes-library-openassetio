# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the Traits node."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import griptape_nodes_library_openassetio.traits_node as traits_node_mod
import pytest
from griptape_nodes.exe_types.core_types import BadgeData, Parameter, ParameterGroup, ParameterMode
from griptape_nodes.exe_types.node_types import DataNode, NodeDependencies
from griptape_nodes_library_openassetio.traits_node import Traits, TraitUsage
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from pathlib import Path

    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


@pytest.fixture
def _mock_trait_catalogue(monkeypatch: pytest.MonkeyPatch, stub_trait_catalogue: TraitCatalogue) -> None:
    """Replace ``_get_trait_catalogue`` so nodes get a test catalogue without the registry."""
    monkeypatch.setattr(traits_node_mod, "_get_trait_catalogue", lambda _metadata: stub_trait_catalogue)


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsStructure:
    """Tests for the Traits node parameter structure."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a fresh Traits node."""
        return Traits(name="test_traits")

    def test_is_data_node(self, node: Traits) -> None:
        """Traits should extend DataNode."""
        assert isinstance(node, DataNode)

    def test_has_traits_data_in_parameter(self, node: Traits) -> None:
        """traits_data_in should be INPUT-only and accept TraitsData."""
        param = node.get_parameter_by_name("traits_data_in")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_traits_data_in_is_not_serializable(self, node: Traits) -> None:
        """TraitsData is not JSON-serializable."""
        param = node.get_parameter_by_name("traits_data_in")
        assert param is not None
        assert param.serializable is False

    def test_has_usage_parameter(self, node: Traits) -> None:
        """Usage should be PROPERTY-only with Options dropdown."""
        param = node.get_parameter_by_name("usage")
        assert param is not None
        assert param.allowed_modes == {ParameterMode.PROPERTY}
        assert param.default_value == TraitUsage.ENTITY.value

    def test_usage_parameter_has_options(self, node: Traits) -> None:
        """Usage should have an Options trait with all TraitUsage values."""
        param = node.get_parameter_by_name("usage")
        assert param is not None
        choices = param.ui_options["simple_dropdown"]
        expected = [u.value for u in TraitUsage]
        assert choices == expected

    def test_has_trait_ids_parameter(self, node: Traits) -> None:
        """trait_ids should be PROPERTY-only (not wireable)."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        assert param.allowed_modes == {ParameterMode.PROPERTY}

    def test_trait_ids_has_multi_options(self, node: Traits) -> None:
        """trait_ids should have a MultiOptions trait with the catalogue's IDs."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        ui_opts = param.ui_options
        assert "multi_options" in ui_opts
        assert ui_opts["multi_options"]["show_search"] is True
        assert ui_opts["multi_options"]["allow_user_created_options"] is False
        choices = ui_opts["multi_options"]["choices"]
        assert "test:content.LocatableContent" in choices
        assert "test:identity.DisplayName" in choices

    def test_trait_ids_choices_include_specifications(self, node: Traits) -> None:
        """Specifications should appear in the MultiOptions choices."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        choices = param.ui_options["multi_options"]["choices"]
        assert "test:specification:content.NamedContent" in choices

    def test_has_traits_data_out_parameter(self, node: Traits) -> None:
        """traits_data_out should be OUTPUT-only."""
        param = node.get_parameter_by_name("traits_data_out")
        assert param is not None
        assert param.output_type == "TraitsData"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_traits_data_out_is_not_serializable(self, node: Traits) -> None:
        """TraitsData is not JSON-serializable."""
        param = node.get_parameter_by_name("traits_data_out")
        assert param is not None
        assert param.serializable is False

    def test_has_output_trait_ids_parameter(self, node: Traits) -> None:
        """output_trait_ids should be a read-only multiline string in a collapsed group."""
        param = node.get_parameter_by_name("output_trait_ids")
        assert param is not None
        assert param.type == "str"
        assert param.allowed_modes == {ParameterMode.PROPERTY}
        assert param.serializable is False
        assert param.settable is False
        assert param.ui_options.get("multiline") is True

        group = node.get_group_by_name_or_element_id("Output Trait IDs")
        assert group is not None
        assert group.collapsed is True
        assert param.parent_group_name == "Output Trait IDs"

    def test_default_metadata(self, node: Traits) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        """Passing metadata should merge with the default node metadata."""
        node = Traits(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"


@pytest.mark.usefixtures("griptape_nodes")
class TestTraitsCatalogueLookup:
    """Tests for the catalogue lookup via _get_trait_catalogue."""

    def test_constructs_without_library_metadata(self) -> None:
        """Constructing without metadata['library'] should succeed with empty catalogue."""
        node = Traits(name="no_library")
        assert len(node._trait_catalogue.choosable_ids_for_usage("entity")) == 0  # noqa: SLF001
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        assert param.ui_options["multi_options"]["choices"] == []


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsDynamicParameters:
    """Tests for dynamic parameter creation and group management."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a node with a mocked transition component."""
        node = Traits(name="test_entity_traits_dyn")
        node._transition_component = create_autospec(node._transition_component)  # noqa: SLF001
        return node

    def test_build_desired_params_returns_correct_descriptors(self, node: Traits) -> None:
        """_build_desired_params should return TransitionParameter for each property."""
        params = node._build_desired_params(["test:content.LocatableContent"])  # noqa: SLF001

        names = [p.name for p in params]
        assert "test:content.LocatableContent.location" in names
        assert "test:content.LocatableContent.mimeType" in names

        location = next(p for p in params if p.name == "test:content.LocatableContent.location")
        assert location.output_type == "str"
        # Key difference from ResolveEntity: INPUT+OUTPUT modes.
        assert location.allowed_modes == frozenset({ParameterMode.INPUT, ParameterMode.OUTPUT})
        assert location.input_types == frozenset({"str"})

    def test_build_desired_params_maps_property_types(self, node: Traits) -> None:
        """Property types (integer, float, boolean) should map to Griptape types."""
        params = node._build_desired_params(["test:types.Mixed"])  # noqa: SLF001

        by_name = {p.name: p for p in params}
        assert by_name["test:types.Mixed.count"].output_type == "int"
        assert by_name["test:types.Mixed.count"].input_types == frozenset({"int"})
        assert by_name["test:types.Mixed.ratio"].output_type == "float"
        assert by_name["test:types.Mixed.enabled"].output_type == "bool"

    def test_build_desired_params_skips_unknown_trait_ids(self, node: Traits) -> None:
        """Unknown trait IDs should be silently skipped."""
        params = node._build_desired_params(["unknown:trait.Id"])  # noqa: SLF001
        assert params == []

    def test_ensure_trait_groups_creates_hierarchy(self, node: Traits) -> None:
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

    def test_ensure_trait_groups_is_idempotent(self, node: Traits) -> None:
        """Calling _ensure_trait_groups_exist twice should not duplicate groups."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001
        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        all_groups = node.root_ui_element.find_elements_by_type(ParameterGroup)
        names = [g.name for g in all_groups if g.user_defined]
        assert names.count("test") == 1
        assert names.count("test:content") == 1
        assert names.count("test:content.LocatableContent") == 1

    def test_ensure_trait_groups_shares_package_across_namespaces(self, node: Traits) -> None:
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
        assert content_ns.parent_group_name == "test"
        assert identity_ns.parent_group_name == "test"

    def test_v2_trait_member_group_display_name(self, node: Traits) -> None:
        """v2+ traits should have display name 'MemberName (v2)' on member group."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent.v2")  # noqa: SLF001
        assert defn is not None

        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        member = node.get_group_by_name_or_element_id("test:content.LocatableContent.v2")
        assert member is not None
        assert member.ui_options.get("display_name") == "LocatableContent (v2)"

    def test_package_group_has_badge(self, node: Traits) -> None:
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

    def test_namespace_group_has_badge(self, node: Traits) -> None:
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

    def test_member_group_has_badge(self, node: Traits) -> None:
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

    def test_remove_stale_groups_prunes_empty_package(self, node: Traits) -> None:
        """Package groups with no Parameter descendants should be removed."""
        defn = node._trait_catalogue.get_trait("test:content.LocatableContent")  # noqa: SLF001
        assert defn is not None
        node._ensure_trait_groups_exist(defn)  # noqa: SLF001

        assert node.get_group_by_name_or_element_id("test") is not None

        node._remove_stale_groups()  # noqa: SLF001

        assert node.get_group_by_name_or_element_id("test") is None
        assert node.get_group_by_name_or_element_id("test:content") is None
        assert node.get_group_by_name_or_element_id("test:content.LocatableContent") is None

    def test_after_value_set_calls_rebuild(self, node: Traits) -> None:
        """Setting trait_ids should trigger _rebuild_dynamic_params."""
        rebuild_mock = create_autospec(node._rebuild_dynamic_params)  # noqa: SLF001
        node._rebuild_dynamic_params = rebuild_mock  # noqa: SLF001

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])

        rebuild_mock.assert_called_once_with(["test:content.LocatableContent"])

    def test_badge_set_on_package_group_added_outside_ensure(self, node: Traits) -> None:
        """Badge should appear when a user_defined package group is added directly.

        During deserialization, groups are created by the engine handler (not by
        _ensure_trait_groups_exist), so badges must be set by the lifecycle hook.
        """
        pkg_group = ParameterGroup(name="test", user_defined=True, ui_options={"display_name": "test"})
        node.add_node_element(pkg_group)

        badge = pkg_group.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Test package description"

    def test_badge_set_on_namespace_group_added_via_add_child(self, node: Traits) -> None:
        """Badge should appear on a nested namespace group added via add_child."""
        pkg_group = ParameterGroup(name="test", user_defined=True)
        node.add_node_element(pkg_group)

        ns_group = ParameterGroup(name="test:content", user_defined=True)
        pkg_group.add_child(ns_group)

        badge = ns_group.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Content namespace description"

    def test_badge_set_on_member_group_added_via_add_child(self, node: Traits) -> None:
        """Badge should appear on a nested member group added via add_child."""
        pkg_group = ParameterGroup(name="test", user_defined=True)
        node.add_node_element(pkg_group)
        ns_group = ParameterGroup(name="test:content", user_defined=True)
        pkg_group.add_child(ns_group)

        member_group = ParameterGroup(name="test:content.LocatableContent", user_defined=True)
        ns_group.add_child(member_group)

        badge = member_group.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "Locatable content trait"

    def test_badge_set_on_parameter_added_via_add_child(self, node: Traits) -> None:
        """Badge should appear on a user_defined parameter added via add_child."""
        pkg_group = ParameterGroup(name="test", user_defined=True)
        node.add_node_element(pkg_group)
        ns_group = ParameterGroup(name="test:content", user_defined=True)
        pkg_group.add_child(ns_group)
        member_group = ParameterGroup(name="test:content.LocatableContent", user_defined=True)
        ns_group.add_child(member_group)

        param = Parameter(
            name="test:content.LocatableContent.location",
            type="str",
            tooltip="The location",
            allowed_modes={ParameterMode.INPUT, ParameterMode.OUTPUT},
            user_defined=True,
        )
        member_group.add_child(param)

        badge = param.get_badge()
        assert badge is not None
        assert badge.variant == "info"
        assert badge.message == "The location"

    def test_existing_badge_not_overwritten_by_lifecycle_hook(self, node: Traits) -> None:
        """Elements that already have badges should not be overwritten."""
        pkg_group = ParameterGroup(
            name="test",
            user_defined=True,
            badge=BadgeData(variant="warning", message="Custom badge"),
        )
        node.add_node_element(pkg_group)

        badge = pkg_group.get_badge()
        assert badge is not None
        assert badge.variant == "warning"
        assert badge.message == "Custom badge"


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsUsageDropdown:
    """Tests for the usage dropdown and trait_ids choice updates."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a node with a mocked transition component."""
        node = Traits(name="test_traits_usage")
        node._transition_component = create_autospec(node._transition_component)  # noqa: SLF001
        return node

    def test_default_trait_ids_choices_are_entity_usage(
        self, node: Traits, stub_trait_catalogue: TraitCatalogue
    ) -> None:
        """Initial trait_ids choices should be filtered to entity usage."""
        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        choices = param.ui_options["multi_options"]["choices"]
        expected = stub_trait_catalogue.choosable_ids_for_usage("entity")
        assert choices == expected

    def test_changing_usage_updates_trait_ids_choices(self, node: Traits, stub_trait_catalogue: TraitCatalogue) -> None:
        """Changing usage should update the trait_ids choices to match."""
        node.set_parameter_value("usage", "locale")

        param = node.get_parameter_by_name("trait_ids")
        assert param is not None
        choices = param.ui_options["multi_options"]["choices"]
        expected = stub_trait_catalogue.choosable_ids_for_usage("locale")
        assert choices == expected

    def test_changing_usage_clears_stale_trait_ids(self, node: Traits) -> None:
        """Changing usage should remove trait_ids that are not valid for the new usage."""
        # Select an entity trait.
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        # Switch to locale — entity traits are no longer valid.
        node.set_parameter_value("usage", "locale")

        current: list[str] = node.parameter_values.get("trait_ids", [])
        assert "test:content.LocatableContent" not in current

    def test_changing_usage_preserves_valid_trait_ids(self, node: Traits) -> None:
        """Changing usage should keep trait_ids that are valid for the new usage."""
        # DisplayName has usage=["entity", "locale"], so it is valid in both.
        node.set_parameter_value("trait_ids", ["test:identity.DisplayName"])
        # Switch to locale — DisplayName should survive the prune.
        node.set_parameter_value("usage", "locale")

        current: list[str] = node.parameter_values.get("trait_ids", [])
        assert "test:identity.DisplayName" in current

    def test_changing_usage_twice_tracks_trait_ids_for_ui_update(self, node: Traits) -> None:
        """Changing usage a second time should still track trait_ids for UI update.

        Regression test: the first usage change populates ``_ui_options`` with a
        ``multi_options`` dict. On the second change, ``ui_options`` (the property
        getter) returns a shallow merge whose ``multi_options`` value is a shared
        reference into ``_ui_options``. If the code mutates that dict in place before
        passing it to ``update_ui_options_key``, the ``old != new`` check in
        ``emits_update_on_write`` sees identical values and the parameter is never
        tracked — leaving the frontend stale. The fix is to build a fresh dict so the
        comparison sees a genuine change.
        """
        # Select a trait valid in both entity and locale so pruned == current
        # (no set_parameter_value("trait_ids", ...) call to mask the issue).
        node.set_parameter_value("trait_ids", ["test:identity.DisplayName"])

        # First usage change: populates _ui_options with multi_options.
        node.set_parameter_value("usage", "locale")

        trait_ids_param = node.get_parameter_by_name("trait_ids")
        assert trait_ids_param is not None
        # Clear tracked changes so we only observe the second switch.
        node._tracked_parameters.clear()  # noqa: SLF001

        # Second usage change: this is the one that would fail with
        # in-place mutation.
        node.set_parameter_value("usage", "entity")

        assert trait_ids_param in node._tracked_parameters  # noqa: SLF001

    def test_after_value_set_usage_calls_update_choices(self, node: Traits) -> None:
        """Setting usage should trigger _update_trait_ids_choices."""
        update_mock = create_autospec(node._update_trait_ids_choices)  # noqa: SLF001
        node._update_trait_ids_choices = update_mock  # noqa: SLF001

        node.set_parameter_value("usage", "locale")

        update_mock.assert_called_once_with("locale")


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsProcess:
    """Tests for the Traits process() method."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a fresh Traits node."""
        return Traits(name="test_entity_traits_proc")

    def test_process_builds_traits_data(self, node: Traits) -> None:
        """process() should build a TraitsData and output per-property values."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert isinstance(td, TraitsData)
        assert "test:content.LocatableContent" in td.traitSet()
        # No upstream or overrides — property outputs are None.
        assert node.parameter_output_values["test:content.LocatableContent.location"] is None
        assert node.parameter_output_values["test:content.LocatableContent.mimeType"] is None

    def test_process_with_no_traits_outputs_empty_traits_data(self, node: Traits) -> None:
        """process() with no traits selected should output an empty TraitsData."""
        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert isinstance(td, TraitsData)
        assert td.traitSet() == set()

    def test_process_with_no_traits_passes_through_upstream(self, node: Traits) -> None:
        """process() with no traits selected should pass through upstream TraitsData."""
        upstream = TraitsData({"some:extra.Trait"})
        node.parameter_values["traits_data_in"] = upstream

        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert isinstance(td, TraitsData)
        assert "some:extra.Trait" in td.traitSet()

    def test_process_override_takes_priority(self, node: Traits) -> None:
        """Override values set on dynamic parameters should appear in the output."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.parameter_values["test:content.LocatableContent.location"] = "file:///override.exr"

        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert td.getTraitProperty("test:content.LocatableContent", "location") == "file:///override.exr"
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///override.exr"

    def test_process_merges_upstream_traits_data(self, node: Traits) -> None:
        """Upstream TraitsData values should flow through to outputs."""
        upstream = TraitsData({"test:content.LocatableContent"})
        upstream.setTraitProperty("test:content.LocatableContent", "location", "file:///upstream.exr")

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.parameter_values["traits_data_in"] = upstream

        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert td.getTraitProperty("test:content.LocatableContent", "location") == "file:///upstream.exr"
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///upstream.exr"

    def test_process_expands_specification_to_trait_ids(self, node: Traits) -> None:
        """process() should expand specification IDs into their constituent traits."""
        node.set_parameter_value("trait_ids", ["test:specification:content.NamedContent"])
        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert isinstance(td, TraitsData)
        assert "test:content.LocatableContent" in td.traitSet()
        assert "test:identity.DisplayName" in td.traitSet()

    def test_process_specification_applies_overrides(self, node: Traits) -> None:
        """process() should apply overrides to properties from expanded specification traits."""
        node.set_parameter_value("trait_ids", ["test:specification:content.NamedContent"])
        node.parameter_values["test:content.LocatableContent.location"] = "file:///spec.exr"

        node.process()

        td = node.parameter_output_values["traits_data_out"]
        assert isinstance(td, TraitsData)
        assert td.getTraitProperty("test:content.LocatableContent", "location") == "file:///spec.exr"
        assert node.parameter_output_values["test:content.LocatableContent.location"] == "file:///spec.exr"

    def test_process_populates_output_trait_ids(self, node: Traits) -> None:
        """process() should populate output_trait_ids with a sorted multiline string."""
        node.set_parameter_value("trait_ids", ["test:content.LocatableContent", "test:identity.DisplayName"])
        node.process()

        expected = "test:content.LocatableContent\ntest:identity.DisplayName"
        assert node.parameter_values["output_trait_ids"] == expected

    def test_process_output_trait_ids_includes_upstream_traits(self, node: Traits) -> None:
        """output_trait_ids should include upstream traits not in the selection."""
        upstream = TraitsData({"some:extra.Trait"})

        node.set_parameter_value("trait_ids", ["test:content.LocatableContent"])
        node.parameter_values["traits_data_in"] = upstream

        node.process()

        value = node.parameter_values["output_trait_ids"]
        assert "some:extra.Trait" in value
        assert "test:content.LocatableContent" in value


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsValidateBeforeWorkflowRun:
    """Tests for divergence detection in validate_before_workflow_run()."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a fresh Traits node."""
        return Traits(name="test_traits_validate")

    def test_warns_on_unknown_selected_trait(self, node: Traits, caplog: pytest.LogCaptureFixture) -> None:
        """A selected trait absent from the current catalogue emits a warning."""
        # Set via parameter_values directly to avoid triggering dynamic-parameter
        # rebuild (which needs engine registration unavailable in unit tests).
        node.parameter_values["trait_ids"] = ["test:content.LocatableContent", "gone:content.Vanished"]

        with caplog.at_level(logging.WARNING):
            result = node.validate_before_workflow_run()

        assert result is None
        assert "gone:content.Vanished" in caplog.text
        assert "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS" in caplog.text
        assert node.name in caplog.text
        # A trait that IS present must not be named as missing.
        assert "test:content.LocatableContent" not in caplog.text

    def test_no_warning_when_all_traits_present(self, node: Traits, caplog: pytest.LogCaptureFixture) -> None:
        """No divergence warning is emitted when all selected traits are in the catalogue."""
        node.parameter_values["trait_ids"] = ["test:content.LocatableContent"]

        with caplog.at_level(logging.WARNING):
            result = node.validate_before_workflow_run()

        assert result is None
        assert "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS" not in caplog.text

    def test_no_warning_when_nothing_selected(self, node: Traits, caplog: pytest.LogCaptureFixture) -> None:
        """No divergence warning is emitted when no traits are selected."""
        with caplog.at_level(logging.WARNING):
            result = node.validate_before_workflow_run()

        assert result is None
        assert "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS" not in caplog.text


@pytest.mark.usefixtures("griptape_nodes", "_mock_trait_catalogue")
class TestTraitsGetNodeDependencies:
    """Tests for get_node_dependencies() on the Traits node."""

    @pytest.fixture
    def node(self) -> Traits:
        """Create a fresh Traits node."""
        return Traits(name="test_traits_deps")

    def test_declares_env_var_files_as_static_files(
        self, node: Traits, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Trait definition files from the env var are declared as static file dependencies."""
        file_a = tmp_path / "a.yml"
        file_a.write_text("a")
        file_b = tmp_path / "b.yml"
        file_b.write_text("b")
        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", f"{file_a}{os.pathsep}{file_b}")

        deps = node.get_node_dependencies()

        assert deps is not None
        assert {str(file_a), str(file_b)} <= deps.static_files

    def test_returns_none_when_no_dependencies(self, node: Traits, monkeypatch: pytest.MonkeyPatch) -> None:
        """No env var files and no base dependencies yields None."""
        monkeypatch.delenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", raising=False)

        assert node.get_node_dependencies() is None

    def test_aggregates_base_dependencies(self, node: Traits, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Base class dependencies are preserved alongside the env-var static files."""
        base_deps = NodeDependencies(static_files={"base-sentinel.json"})
        monkeypatch.setattr(traits_node_mod.DataNode, "get_node_dependencies", lambda _self: base_deps)
        yaml_file = tmp_path / "c.yml"
        yaml_file.write_text("c")
        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        deps = node.get_node_dependencies()

        assert deps is not None
        assert "base-sentinel.json" in deps.static_files
        assert str(yaml_file) in deps.static_files
