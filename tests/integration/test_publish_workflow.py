# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the publish workflow (preflight -> register) using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes_library_openassetio.preflight_entity_node import PreflightEntity
from griptape_nodes_library_openassetio.register_entity_node import RegisterEntity
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession

# Existing entity in the BAL publish config.
_ENTITY_REF = "bal:///test/publish_target"


@pytest.mark.usefixtures("griptape_nodes", "openassetio_publish_config_env")
class TestPublishWorkflow:
    """End-to-end publish workflow against the BAL manager."""

    @pytest.fixture
    def session(self) -> ManagerSession:
        """Create a real BAL-backed session."""
        session_node = OpenAssetIOSession(name="session")
        session_node.process()
        return session_node.parameter_output_values["session"]

    def test_preflight_then_register_publishes_entity(
        self,
        session: ManagerSession,
    ) -> None:
        """A full preflight -> register cycle should succeed."""
        # Build a TraitsData with the traits BAL expects for this entity.
        traits_data = TraitsData(
            {
                "openassetio-mediacreation:usage.Entity",
                "openassetio-mediacreation:content.LocatableContent",
            }
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "location",
            "file:///mnt/assets/test/published_output.exr",
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "mimeType",
            "image/x-exr",
        )

        # --- Preflight ---
        preflight_node = PreflightEntity(name="test_preflight")
        preflight_node.parameter_values["session"] = session
        preflight_node.parameter_values["entity_reference"] = _ENTITY_REF
        preflight_node.parameter_values["traits_data"] = traits_data

        preflight_node.process()

        assert preflight_node._execution_succeeded is True  # noqa: SLF001
        working_reference = preflight_node.parameter_output_values["working_reference"]
        assert isinstance(working_reference, str)
        assert working_reference  # non-empty

        # --- Register ---
        register_node = RegisterEntity(name="test_register")
        # Wire outputs from preflight to register inputs.
        register_node.parameter_values["session"] = preflight_node.parameter_output_values["session"]
        register_node.parameter_values["working_reference"] = working_reference
        register_node.parameter_values["traits_data"] = preflight_node.parameter_output_values["traits_data"]
        register_node.parameter_values["publishing_access"] = preflight_node.parameter_output_values[
            "publishing_access"
        ]

        register_node.process()

        assert register_node._execution_succeeded is True  # noqa: SLF001
        final_reference = register_node.parameter_output_values["final_reference"]
        assert isinstance(final_reference, str)
        assert final_reference  # non-empty

    def test_preflight_passes_through_session(
        self,
        session: ManagerSession,
    ) -> None:
        """PreflightEntity should pass the session object through."""
        traits_data = TraitsData(
            {
                "openassetio-mediacreation:usage.Entity",
                "openassetio-mediacreation:content.LocatableContent",
            }
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "location",
            "file:///mnt/assets/test/published_output.exr",
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "mimeType",
            "image/x-exr",
        )

        preflight_node = PreflightEntity(name="test_preflight_passthrough")
        preflight_node.parameter_values["session"] = session
        preflight_node.parameter_values["entity_reference"] = _ENTITY_REF
        preflight_node.parameter_values["traits_data"] = traits_data

        preflight_node.process()

        assert preflight_node.parameter_output_values["session"] is session

    def test_register_passes_through_session(
        self,
        session: ManagerSession,
    ) -> None:
        """RegisterEntity should pass the session object through."""
        traits_data = TraitsData(
            {
                "openassetio-mediacreation:usage.Entity",
                "openassetio-mediacreation:content.LocatableContent",
            }
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "location",
            "file:///mnt/assets/test/published_output.exr",
        )
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "mimeType",
            "image/x-exr",
        )

        # Preflight first to get a working reference.
        preflight_node = PreflightEntity(name="test_preflight_for_register")
        preflight_node.parameter_values["session"] = session
        preflight_node.parameter_values["entity_reference"] = _ENTITY_REF
        preflight_node.parameter_values["traits_data"] = traits_data
        preflight_node.process()

        register_node = RegisterEntity(name="test_register_passthrough")
        register_node.parameter_values["session"] = preflight_node.parameter_output_values["session"]
        register_node.parameter_values["working_reference"] = preflight_node.parameter_output_values[
            "working_reference"
        ]
        register_node.parameter_values["traits_data"] = preflight_node.parameter_output_values["traits_data"]
        register_node.parameter_values["publishing_access"] = preflight_node.parameter_output_values[
            "publishing_access"
        ]
        register_node.process()

        assert register_node.parameter_output_values["session"] is session

    def test_preflight_nonexistent_entity_succeeds_for_new_publish(
        self,
        session: ManagerSession,
    ) -> None:
        """Publishing a new entity (not in BAL) should succeed at preflight."""
        traits_data = TraitsData({"openassetio-mediacreation:content.LocatableContent"})
        traits_data.setTraitProperty(
            "openassetio-mediacreation:content.LocatableContent",
            "location",
            "file:///mnt/assets/test/new_entity.exr",
        )

        preflight_node = PreflightEntity(name="test_preflight_new")
        preflight_node.parameter_values["session"] = session
        preflight_node.parameter_values["entity_reference"] = "bal:///test/new_entity"
        preflight_node.parameter_values["traits_data"] = traits_data

        preflight_node.process()

        assert preflight_node._execution_succeeded is True  # noqa: SLF001
