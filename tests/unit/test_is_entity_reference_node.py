# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the IsEntityReference node."""

from __future__ import annotations

from unittest.mock import Mock, create_autospec

import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.is_entity_reference_node import IsEntityReference
from griptape_nodes_library_openassetio.session import ManagerSession
from openassetio import Context
from openassetio.hostApi import HostInterface, Manager


def _make_session(*, is_ref_return: bool = True) -> ManagerSession:
    """Build a mock ManagerSession whose manager.isEntityReferenceString returns the given value."""
    mock_manager = Mock(spec=Manager)
    mock_manager.isEntityReferenceString.return_value = is_ref_return
    return ManagerSession(
        manager=mock_manager,
        context=Mock(spec=Context),
        host_interface=Mock(spec=HostInterface),
    )


@pytest.mark.usefixtures("griptape_nodes")
class TestIsEntityReference:
    """Tests for the IsEntityReference node."""

    @pytest.fixture
    def node(self) -> IsEntityReference:
        return IsEntityReference(name="test_is_ref")

    # -- Structure --

    def test_is_success_failure_node(self, node: IsEntityReference) -> None:
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_input_parameter(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_session_parameter_is_not_serializable(self, node: IsEntityReference) -> None:
        """ManagerSession is not JSON-serializable, so the parameter must opt out."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_input_property_parameter(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_has_is_entity_reference_output_parameter(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("is_entity_reference")
        assert param is not None
        assert param.output_type == "bool"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_default_metadata(self, node: IsEntityReference) -> None:
        assert node.metadata["category"] == "OpenAssetIO"

    # -- process() success paths --

    def test_process_outputs_true_for_valid_reference(self, node: IsEntityReference) -> None:
        session = _make_session(is_ref_return=True)
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is True
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: 'asset://my/thing' is a valid entity reference"
        )

    def test_process_outputs_false_for_invalid_reference(self, node: IsEntityReference) -> None:
        session = _make_session(is_ref_return=False)
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "not-a-reference"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is False
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"]
            == "SUCCESS: 'not-a-reference' is not a valid entity reference"
        )

    def test_process_calls_manager_with_value(self, node: IsEntityReference) -> None:
        # Inline construction so mock_manager stays Mock-typed for assertions.
        mock_manager = Mock(spec=Manager)
        mock_manager.isEntityReferenceString.return_value = True
        session = ManagerSession(
            manager=mock_manager,
            context=Mock(spec=Context),
            host_interface=Mock(spec=HostInterface),
        )
        node.parameter_values["session"] = session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        mock_manager.isEntityReferenceString.assert_called_once_with("asset://my/thing")

    # -- process() failure paths --

    def test_process_fails_when_session_is_missing(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = "asset://my/thing"

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        node._handle_failure_exception = mock_handle  # noqa: SLF001

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: No session connected"

    def test_process_fails_when_entity_reference_is_missing(self, node: IsEntityReference) -> None:
        session = _make_session()
        node.parameter_values["session"] = session

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        node._handle_failure_exception = mock_handle  # noqa: SLF001

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: No entity reference provided"
