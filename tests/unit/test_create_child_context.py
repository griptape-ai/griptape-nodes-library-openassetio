# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for create_child_context business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

from griptape_nodes_library_openassetio.create_child_context import create_child_context
from openassetio import Context
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


class TestCreateChildContext:
    """Tests for the create_child_context() function."""

    def test_calls_create_child_context_with_parent_context(self, mock_session: ManagerSession) -> None:
        """create_child_context should create a child context from the parent."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        create_child_context(mock_session, TraitsData({"trait:A"}))

        mock_manager.createChildContext.assert_called_once_with(mock_session.context)

    def test_merges_locale_traits_into_child_context(self, mock_session: ManagerSession) -> None:
        """Input locale traits should be merged into the child context locale."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        locale = TraitsData({"trait:A"})
        locale.setTraitProperty("trait:A", "key", "value")

        result = create_child_context(mock_session, locale)

        assert result.context.locale.getTraitProperty("trait:A", "key") == "value"

    def test_merges_multiple_traits_and_properties(self, mock_session: ManagerSession) -> None:
        """Multiple traits with multiple properties should all be merged."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        locale = TraitsData({"trait:A", "trait:B"})
        locale.setTraitProperty("trait:A", "name", "shot01")
        locale.setTraitProperty("trait:B", "token", "abc123")
        locale.setTraitProperty("trait:B", "expiry", 3600)

        result = create_child_context(mock_session, locale)

        assert result.context.locale.getTraitProperty("trait:A", "name") == "shot01"
        assert result.context.locale.getTraitProperty("trait:B", "token") == "abc123"
        assert result.context.locale.getTraitProperty("trait:B", "expiry") == 3600

    def test_preserves_existing_parent_locale_traits(self, mock_session: ManagerSession) -> None:
        """Traits already on the parent locale should survive the merge."""
        mock_manager = cast("Mock", mock_session.manager)
        child_locale = TraitsData({"trait:Existing"})
        child_locale.setTraitProperty("trait:Existing", "colour", "red")
        child_context = Mock(spec=Context)
        child_context.locale = child_locale
        mock_manager.createChildContext.return_value = child_context

        locale = TraitsData({"trait:New"})
        locale.setTraitProperty("trait:New", "shot", "010")

        result = create_child_context(mock_session, locale)

        assert result.context.locale.getTraitProperty("trait:Existing", "colour") == "red"
        assert result.context.locale.getTraitProperty("trait:New", "shot") == "010"

    def test_returns_new_session_with_same_manager(self, mock_session: ManagerSession) -> None:
        """Returned session should reuse the original manager."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        result = create_child_context(mock_session, TraitsData({"trait:A"}))

        assert result.manager is mock_session.manager

    def test_returns_new_session_with_same_host_interface(self, mock_session: ManagerSession) -> None:
        """Returned session should reuse the original host interface."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        result = create_child_context(mock_session, TraitsData({"trait:A"}))

        assert result.host_interface is mock_session.host_interface

    def test_returns_new_session_with_child_context(self, mock_session: ManagerSession) -> None:
        """Returned session should use the child context, not the parent."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        result = create_child_context(mock_session, TraitsData({"trait:A"}))

        assert result.context is child_context

    def test_does_not_modify_original_session(self, mock_session: ManagerSession) -> None:
        """The original session should not be mutated."""
        mock_manager = cast("Mock", mock_session.manager)
        original_context = mock_session.context
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        result = create_child_context(mock_session, TraitsData({"trait:A"}))

        assert mock_session.context is original_context
        assert result is not mock_session

    def test_handles_traits_with_no_properties(self, mock_session: ManagerSession) -> None:
        """Traits with no properties should still be added to the locale."""
        mock_manager = cast("Mock", mock_session.manager)
        child_context = Mock(spec=Context)
        child_context.locale = TraitsData()
        mock_manager.createChildContext.return_value = child_context

        locale = TraitsData({"trait:Empty"})

        result = create_child_context(mock_session, locale)

        assert "trait:Empty" in result.context.locale.traitSet()

    def test_no_locale_skips_merge(self, mock_session: ManagerSession) -> None:
        """When locale is None, the child locale should be left unchanged."""
        mock_manager = cast("Mock", mock_session.manager)
        child_locale = TraitsData({"trait:Parent"})
        child_locale.setTraitProperty("trait:Parent", "key", "original")
        child_context = Mock(spec=Context)
        child_context.locale = child_locale
        mock_manager.createChildContext.return_value = child_context

        result = create_child_context(mock_session)

        assert result.context.locale.getTraitProperty("trait:Parent", "key") == "original"
        assert result.context.locale.traitSet() == {"trait:Parent"}
