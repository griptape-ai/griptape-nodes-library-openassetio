# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the IsEntityReference node using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes_library_openassetio.is_entity_reference_node import IsEntityReference
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes", "openassetio_minimal_config_env")
class TestIsEntityReference:
    """Integration tests exercising IsEntityReference against the BAL manager."""

    @pytest.fixture
    def session(self) -> ManagerSession:
        """Create a real BAL-backed session."""
        session_node = OpenAssetIOSession(name="session")
        session_node.process()
        return session_node.parameter_output_values["session"]

    @pytest.fixture
    def node(self, session: ManagerSession) -> IsEntityReference:
        """Create an IsEntityReference node wired to a real session."""
        node = IsEntityReference(name="test_is_ref")
        node.parameter_values["session"] = session
        return node

    def test_bal_reference_is_recognised(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = "bal:///cat"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is True

    def test_non_reference_is_rejected(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = "not-a-reference"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is False

    def test_empty_string_is_rejected(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = ""

        # Empty string triggers the "no value" guard, which raises when the
        # failure output is not wired.
        with pytest.raises(ValueError, match="No entity reference provided"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001

    def test_success_status_is_set(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = "bal:///cat"

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
