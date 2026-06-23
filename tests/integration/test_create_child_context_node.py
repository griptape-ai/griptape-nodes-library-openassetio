# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the CreateChildContext node using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes_library_openassetio.create_child_context_node import CreateChildContext
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes", "openassetio_minimal_config_env")
class TestCreateChildContext:
    """Integration tests exercising CreateChildContext against the BAL manager."""

    @pytest.fixture
    def session(self) -> ManagerSession:
        """Create a real BAL-backed session."""
        session_node = OpenAssetIOSession(name="session")
        session_node.process()
        return session_node.parameter_output_values["session"]

    def test_child_session_has_different_context(self, session: ManagerSession) -> None:
        """The child session should hold a different context object."""
        node = CreateChildContext(name="test_child_ctx")
        node.parameter_values["session"] = session

        node.process()

        child_session = node.parameter_output_values["child_session"]
        assert child_session.context is not session.context

    def test_child_session_shares_same_manager(self, session: ManagerSession) -> None:
        """The child session should share the same manager instance."""
        node = CreateChildContext(name="test_child_ctx")
        node.parameter_values["session"] = session

        node.process()

        child_session = node.parameter_output_values["child_session"]
        assert child_session.manager is session.manager

    def test_child_session_shares_same_host_interface(self, session: ManagerSession) -> None:
        """The child session should share the same host interface."""
        node = CreateChildContext(name="test_child_ctx")
        node.parameter_values["session"] = session

        node.process()

        child_session = node.parameter_output_values["child_session"]
        assert child_session.host_interface is session.host_interface

    def test_locale_merged_into_child_context(self, session: ManagerSession) -> None:
        """Locale traits should be merged into the child context."""
        locale = TraitsData({"openassetio-mediacreation:usage.Entity"})
        locale.setTraitProperty(
            "openassetio-mediacreation:usage.Entity",
            "name",
            "test-locale-value",
        )

        node = CreateChildContext(name="test_child_ctx")
        node.parameter_values["session"] = session
        node.parameter_values["locale"] = locale

        node.process()

        child_session = node.parameter_output_values["child_session"]
        child_locale = child_session.context.locale
        assert child_locale.getTraitProperty("openassetio-mediacreation:usage.Entity", "name") == "test-locale-value"

    def test_parent_locale_unaffected_by_child_merge(self, session: ManagerSession) -> None:
        """Merging locale into the child should not modify the parent context."""
        locale = TraitsData({"openassetio-mediacreation:usage.Entity"})
        locale.setTraitProperty(
            "openassetio-mediacreation:usage.Entity",
            "name",
            "child-only-value",
        )

        node = CreateChildContext(name="test_child_ctx")
        node.parameter_values["session"] = session
        node.parameter_values["locale"] = locale

        node.process()

        # The parent context's locale should not have the trait.
        assert not session.context.locale.hasTrait("openassetio-mediacreation:usage.Entity")
