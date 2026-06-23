# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for resolve_entity business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from openassetio.access import ResolveAccess
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from unittest.mock import Mock

    from griptape_nodes_library_openassetio.session import ManagerSession


class TestResolveEntity:
    """Tests for the resolve_entity() function."""

    def test_returns_traits_data_with_resolved_values(self, mock_session: ManagerSession) -> None:
        """resolve_entity should return a TraitsData with resolved property values."""
        mock_manager = cast("Mock", mock_session.manager)

        resolved_td = TraitsData({"test:content.LocatableContent"})
        resolved_td.setTraitProperty("test:content.LocatableContent", "location", "file:///resolved.exr")

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = resolved_td

        input_td = TraitsData({"test:content.LocatableContent"})
        result = resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

        assert "test:content.LocatableContent" in result.traitSet()
        assert result.getTraitProperty("test:content.LocatableContent", "location") == "file:///resolved.exr"

    def test_preserves_input_traits_data(self, mock_session: ManagerSession) -> None:
        """resolve_entity should not modify the input TraitsData."""
        mock_manager = cast("Mock", mock_session.manager)

        resolved_td = TraitsData({"test:content.LocatableContent"})
        resolved_td.setTraitProperty("test:content.LocatableContent", "location", "file:///resolved.exr")

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = resolved_td

        input_td = TraitsData({"test:content.LocatableContent"})
        input_td.setTraitProperty("test:content.LocatableContent", "location", "file:///original.exr")

        resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

        # Input should be unchanged.
        assert input_td.getTraitProperty("test:content.LocatableContent", "location") == "file:///original.exr"

    def test_merges_resolved_values_into_input_copy(self, mock_session: ManagerSession) -> None:
        """resolve_entity should merge resolved values into a copy of the input."""
        mock_manager = cast("Mock", mock_session.manager)

        # Input has two traits; only one is resolved.
        input_td = TraitsData({"test:content.LocatableContent", "test:identity.DisplayName"})
        input_td.setTraitProperty("test:identity.DisplayName", "name", "My Entity")

        resolved_td = TraitsData({"test:content.LocatableContent"})
        resolved_td.setTraitProperty("test:content.LocatableContent", "location", "file:///resolved.exr")

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = resolved_td

        result = resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

        # Both input and resolved traits should be present.
        assert "test:content.LocatableContent" in result.traitSet()
        assert "test:identity.DisplayName" in result.traitSet()
        assert result.getTraitProperty("test:content.LocatableContent", "location") == "file:///resolved.exr"
        assert result.getTraitProperty("test:identity.DisplayName", "name") == "My Entity"

    def test_creates_entity_reference_from_string(self, mock_session: ManagerSession) -> None:
        """resolve_entity should create an entity reference object from the string."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = TraitsData(set())

        resolve_entity(mock_session, "asset://my/entity", TraitsData({"test:ns.Trait"}), ResolveAccess.kRead)

        mock_manager.createEntityReference.assert_called_once_with("asset://my/entity")

    def test_passes_access_mode_to_resolve(self, mock_session: ManagerSession) -> None:
        """resolve_entity should use the provided access mode, not hardcode kRead."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = TraitsData(set())

        input_td = TraitsData({"test:content.LocatableContent"})
        resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kManagerDriven)

        call_args = mock_manager.resolve.call_args[0]
        assert call_args[2] == ResolveAccess.kManagerDriven

    def test_uses_trait_set_from_input(self, mock_session: ManagerSession) -> None:
        """resolve_entity should resolve the trait set from the input TraitsData."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = TraitsData(set())

        input_td = TraitsData({"test:content.LocatableContent", "test:identity.DisplayName"})
        resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

        call_args = mock_manager.resolve.call_args[0]
        assert call_args[1] == {"test:content.LocatableContent", "test:identity.DisplayName"}

    def test_resolved_values_overwrite_input_values(self, mock_session: ManagerSession) -> None:
        """When both input and resolved have the same property, resolved wins."""
        mock_manager = cast("Mock", mock_session.manager)

        # Both input and resolved set the same property to different values.
        input_td = TraitsData({"test:content.LocatableContent"})
        input_td.setTraitProperty("test:content.LocatableContent", "location", "file:///input.exr")

        resolved_td = TraitsData({"test:content.LocatableContent"})
        resolved_td.setTraitProperty("test:content.LocatableContent", "location", "file:///resolved.exr")

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = resolved_td

        result = resolve_entity(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

        # Resolved value should take priority over the input default.
        assert result.getTraitProperty("test:content.LocatableContent", "location") == "file:///resolved.exr"

    def test_propagates_resolve_exception(self, mock_session: ManagerSession) -> None:
        """Exceptions from manager.resolve() propagate to the caller."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.side_effect = RuntimeError("Entity not found")

        with pytest.raises(RuntimeError, match="Entity not found"):
            resolve_entity(mock_session, "asset://missing", TraitsData({"test:ns.Trait"}), ResolveAccess.kRead)
