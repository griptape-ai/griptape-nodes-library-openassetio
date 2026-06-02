# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the OpenAssetIOSession node using BAL."""

from __future__ import annotations

import pytest
from griptape_nodes_library_openassetio.session import (
    ManagerSession,
    _HostInterface,
)
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from openassetio import Context
from openassetio.hostApi import Manager


@pytest.mark.usefixtures("griptape_nodes", "openassetio_minimal_config_env")
class TestOpenAssetIOSession:
    """Integration tests exercising OpenAssetIOSession against the BAL manager."""

    @pytest.fixture
    def node(self) -> OpenAssetIOSession:
        node = OpenAssetIOSession(name="test_session")
        node.process()
        return node

    @pytest.fixture
    def session(self, node: OpenAssetIOSession) -> ManagerSession:
        return node.parameter_output_values["session"]

    def test_process_produces_session_dataclass(self, session: ManagerSession) -> None:
        assert isinstance(session, ManagerSession)

    def test_session_contains_real_manager(self, session: ManagerSession) -> None:
        assert isinstance(session.manager, Manager)

    def test_session_contains_real_context(self, session: ManagerSession) -> None:
        assert isinstance(session.context, Context)

    def test_session_contains_host_interface(self, session: ManagerSession) -> None:
        assert isinstance(session.host_interface, _HostInterface)

    def test_manager_identifier_matches_bal(self, session: ManagerSession) -> None:
        assert session.manager.identifier() == "org.openassetio.examples.manager.bal"

    def test_manager_display_name_matches_bal(self, session: ManagerSession) -> None:
        assert session.manager.displayName() == "Basic Asset Library 📖"

    def test_manager_display_name_output_matches_bal(self, node: OpenAssetIOSession) -> None:
        assert node.parameter_output_values["manager_display_name"] == "Basic Asset Library 📖"

    def test_manager_identifier_output_matches_bal(self, node: OpenAssetIOSession) -> None:
        assert node.parameter_output_values["manager_identifier"] == "org.openassetio.examples.manager.bal"
