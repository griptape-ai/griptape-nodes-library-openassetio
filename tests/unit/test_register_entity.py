# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for register_entity business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from griptape_nodes_library_openassetio.register_entity import register_entity
from openassetio import EntityReference
from openassetio.access import PublishingAccess
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


class TestRegisterEntity:
    """Tests for the register_entity() function."""

    def test_returns_final_reference_string(self, mock_session: ManagerSession) -> None:
        """register_entity should return the final reference as a string."""
        mock_manager = cast("Mock", mock_session.manager)

        final_ref_obj = Mock(spec=EntityReference)
        final_ref_obj.toString.return_value = "bal:///final/ref"
        mock_manager.createEntityReference.return_value = "working_ref_obj"
        mock_manager.register.return_value = final_ref_obj

        result = register_entity(
            mock_session,
            "asset://working/ref",
            Mock(spec=TraitsData),
            PublishingAccess.kWrite,
        )

        assert result == "bal:///final/ref"

    def test_creates_entity_reference_from_working_reference(self, mock_session: ManagerSession) -> None:
        """register_entity should create an entity reference from the working reference."""
        mock_manager = cast("Mock", mock_session.manager)

        final_ref_obj = Mock(spec=EntityReference)
        final_ref_obj.toString.return_value = "bal:///final/ref"
        mock_manager.createEntityReference.return_value = "working_ref_obj"
        mock_manager.register.return_value = final_ref_obj

        register_entity(
            mock_session,
            "asset://working/ref",
            Mock(spec=TraitsData),
            PublishingAccess.kWrite,
        )

        mock_manager.createEntityReference.assert_called_once_with("asset://working/ref")

    def test_passes_correct_arguments_to_register(self, mock_session: ManagerSession) -> None:
        """register_entity should pass all arguments to manager.register()."""
        mock_manager = cast("Mock", mock_session.manager)

        final_ref_obj = Mock(spec=EntityReference)
        final_ref_obj.toString.return_value = "bal:///final/ref"
        mock_manager.createEntityReference.return_value = "working_ref_obj"
        mock_manager.register.return_value = final_ref_obj

        input_td = Mock(spec=TraitsData)
        register_entity(mock_session, "asset://working/ref", input_td, PublishingAccess.kWrite)

        mock_manager.register.assert_called_once_with(
            "working_ref_obj", input_td, PublishingAccess.kWrite, mock_session.context
        )

    def test_passes_create_related_access_to_register(self, mock_session: ManagerSession) -> None:
        """register_entity should pass kCreateRelated when requested."""
        mock_manager = cast("Mock", mock_session.manager)

        final_ref_obj = Mock(spec=EntityReference)
        final_ref_obj.toString.return_value = "bal:///final/ref"
        mock_manager.createEntityReference.return_value = "working_ref_obj"
        mock_manager.register.return_value = final_ref_obj

        input_td = Mock(spec=TraitsData)
        register_entity(mock_session, "asset://working/ref", input_td, PublishingAccess.kCreateRelated)

        mock_manager.register.assert_called_once_with(
            "working_ref_obj", input_td, PublishingAccess.kCreateRelated, mock_session.context
        )

    def test_propagates_register_exception(self, mock_session: ManagerSession) -> None:
        """Exceptions from manager.register() propagate to the caller."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "working_ref_obj"
        mock_manager.register.side_effect = RuntimeError("Registration failed")

        with pytest.raises(RuntimeError, match="Registration failed"):
            register_entity(
                mock_session,
                "asset://working/ref",
                Mock(spec=TraitsData),
                PublishingAccess.kWrite,
            )
