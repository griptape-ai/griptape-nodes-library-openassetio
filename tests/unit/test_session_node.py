# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the OpenAssetIOSession node."""

from __future__ import annotations

from unittest.mock import Mock, create_autospec

import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio import session_node
from griptape_nodes_library_openassetio.session import ManagerSession, create_session
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from openassetio import Context
from openassetio.errors import OpenAssetIOException
from openassetio.hostApi import HostInterface, Manager


@pytest.mark.usefixtures("griptape_nodes")
class TestOpenAssetIOSession:
    """Tests for the OpenAssetIOSession node."""

    @pytest.fixture
    def node(self) -> OpenAssetIOSession:
        return OpenAssetIOSession(name="test_session")

    def test_is_success_failure_node(self, node: OpenAssetIOSession) -> None:
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_output_parameter(self, node: OpenAssetIOSession) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.output_type == "ManagerSession"

    def test_has_informational_output_parameters(self, node: OpenAssetIOSession) -> None:
        for name in ("manager_display_name", "manager_identifier"):
            param = node.get_parameter_by_name(name)
            assert param is not None, f"missing parameter {name}"
            assert param.output_type == "str"
            assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_session_parameter_is_output_only(self, node: OpenAssetIOSession) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: OpenAssetIOSession) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_default_metadata(self, node: OpenAssetIOSession) -> None:
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["description"] == "Initialise an OpenAssetIO session"

    def test_custom_metadata_merges(self) -> None:
        node = OpenAssetIOSession(name="custom", metadata={"description": "Custom desc", "extra": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["description"] == "Custom desc"
        assert node.metadata["extra"] == "val"

    def test_process_populates_outputs_on_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: OpenAssetIOSession,
    ) -> None:
        mock_manager = Mock(spec=Manager)
        mock_manager.displayName.return_value = "Test Manager"
        mock_manager.identifier.return_value = "org.test.manager"
        session = ManagerSession(
            manager=mock_manager, context=Mock(spec=Context), host_interface=Mock(spec=HostInterface)
        )
        monkeypatch.setattr(session_node, "create_session", create_autospec(create_session, return_value=session))

        node.process()

        assert node.parameter_output_values["session"] is session
        assert node.parameter_output_values["manager_display_name"] == "Test Manager"
        assert node.parameter_output_values["manager_identifier"] == "org.test.manager"

    def test_process_sets_success_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: OpenAssetIOSession,
    ) -> None:
        mock_manager = Mock(spec=Manager)
        mock_manager.displayName.return_value = "Test Manager"
        mock_manager.identifier.return_value = "org.test.manager"
        session = ManagerSession(
            manager=mock_manager, context=Mock(spec=Context), host_interface=Mock(spec=HostInterface)
        )
        monkeypatch.setattr(session_node, "create_session", create_autospec(create_session, return_value=session))

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001

    def test_process_sets_failure_status_on_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: OpenAssetIOSession,
    ) -> None:
        monkeypatch.setattr(
            session_node,
            "create_session",
            create_autospec(create_session, side_effect=RuntimeError("no config")),
        )

        with pytest.raises(RuntimeError, match="no config"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001

    def test_process_sets_failure_status_on_openassetio_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: OpenAssetIOSession,
    ) -> None:
        monkeypatch.setattr(
            session_node,
            "create_session",
            create_autospec(create_session, side_effect=OpenAssetIOException("bad plugin")),
        )

        with pytest.raises(OpenAssetIOException, match="bad plugin"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001

    def test_process_returns_without_populating_outputs_when_failure_handled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: OpenAssetIOSession,
    ) -> None:
        monkeypatch.setattr(
            session_node,
            "create_session",
            create_autospec(create_session, side_effect=RuntimeError("no config")),
        )
        mock_handle_failure = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        monkeypatch.setattr(node, "_handle_failure_exception", mock_handle_failure)

        node.process()

        assert "session" not in node.parameter_output_values
