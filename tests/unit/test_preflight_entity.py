# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for preflight_entity business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from griptape_nodes_library_openassetio.preflight_entity import preflight_entity
from openassetio import EntityReference
from openassetio.access import PublishingAccess
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


class TestPreflightEntity:
    """Tests for the preflight_entity() function."""

    def test_returns_working_reference_string(self, mock_session: ManagerSession) -> None:
        """preflight_entity should return the working reference as a string."""
        mock_manager = cast("Mock", mock_session.manager)

        working_ref_obj = Mock(spec=EntityReference)
        working_ref_obj.toString.return_value = "bal:///working/ref"
        mock_manager.createEntityReference.return_value = "entity_ref_obj"
        mock_manager.preflight.return_value = working_ref_obj

        result = preflight_entity(
            mock_session,
            "asset://my/entity",
            Mock(spec=TraitsData),
            PublishingAccess.kWrite,
        )

        assert result == "bal:///working/ref"

    def test_creates_entity_reference_from_string(self, mock_session: ManagerSession) -> None:
        """preflight_entity should create an entity reference from the string."""
        mock_manager = cast("Mock", mock_session.manager)

        working_ref_obj = Mock(spec=EntityReference)
        working_ref_obj.toString.return_value = "bal:///working/ref"
        mock_manager.createEntityReference.return_value = "entity_ref_obj"
        mock_manager.preflight.return_value = working_ref_obj

        preflight_entity(
            mock_session,
            "asset://my/entity",
            Mock(spec=TraitsData),
            PublishingAccess.kWrite,
        )

        mock_manager.createEntityReference.assert_called_once_with("asset://my/entity")

    def test_passes_correct_arguments_to_preflight(self, mock_session: ManagerSession) -> None:
        """preflight_entity should pass all arguments to manager.preflight()."""
        mock_manager = cast("Mock", mock_session.manager)

        working_ref_obj = Mock(spec=EntityReference)
        working_ref_obj.toString.return_value = "bal:///working/ref"
        mock_manager.createEntityReference.return_value = "entity_ref_obj"
        mock_manager.preflight.return_value = working_ref_obj

        input_td = Mock(spec=TraitsData)
        preflight_entity(mock_session, "asset://my/entity", input_td, PublishingAccess.kWrite)

        mock_manager.preflight.assert_called_once_with(
            "entity_ref_obj", input_td, PublishingAccess.kWrite, mock_session.context
        )

    def test_passes_create_related_access_to_preflight(self, mock_session: ManagerSession) -> None:
        """preflight_entity should pass kCreateRelated when requested."""
        mock_manager = cast("Mock", mock_session.manager)

        working_ref_obj = Mock(spec=EntityReference)
        working_ref_obj.toString.return_value = "bal:///working/ref"
        mock_manager.createEntityReference.return_value = "entity_ref_obj"
        mock_manager.preflight.return_value = working_ref_obj

        input_td = Mock(spec=TraitsData)
        preflight_entity(mock_session, "asset://my/entity", input_td, PublishingAccess.kCreateRelated)

        mock_manager.preflight.assert_called_once_with(
            "entity_ref_obj", input_td, PublishingAccess.kCreateRelated, mock_session.context
        )

    def test_propagates_preflight_exception(self, mock_session: ManagerSession) -> None:
        """Exceptions from manager.preflight() propagate to the caller."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "entity_ref_obj"
        mock_manager.preflight.side_effect = RuntimeError("Preflight failed")

        with pytest.raises(RuntimeError, match="Preflight failed"):
            preflight_entity(
                mock_session,
                "asset://my/entity",
                Mock(spec=TraitsData),
                PublishingAccess.kWrite,
            )
