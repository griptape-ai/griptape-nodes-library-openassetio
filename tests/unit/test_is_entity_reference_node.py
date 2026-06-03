# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the IsEntityReference node."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.is_entity_reference_node import IsEntityReference

if TYPE_CHECKING:
    from unittest.mock import Mock

    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestIsEntityReference:
    """Tests for the IsEntityReference node."""

    @pytest.fixture
    def node(self) -> IsEntityReference:
        return IsEntityReference(name="test_is_ref")

    # -- Structure --

    def test_is_success_failure_node(self, node: IsEntityReference) -> None:
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_parameter_with_pass_through(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: IsEntityReference) -> None:
        """ManagerSession is not JSON-serializable, so the parameter must opt out."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_parameter_with_pass_through(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT}

    def test_has_is_entity_reference_output_parameter(self, node: IsEntityReference) -> None:
        param = node.get_parameter_by_name("is_entity_reference")
        assert param is not None
        assert param.output_type == "bool"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_has_fail_if_not_entity_reference_parameter(self, node: IsEntityReference) -> None:
        """The failure toggle defaults to on (mirroring ScanSequence's fail_on_empty_result)."""
        param = node.get_parameter_by_name("fail_if_not_entity_reference")
        assert param is not None
        assert param.type == "bool"
        assert param.default_value is True
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_has_failure_control_output(self, node: IsEntityReference) -> None:
        """SuccessFailureNode exposes a Failed control output for the non-reference path."""
        assert node.get_parameter_by_name("failure") is not None

    def test_default_metadata(self, node: IsEntityReference) -> None:
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        """Passing metadata should merge with the default node metadata."""
        node = IsEntityReference(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"

    # -- validate_before_node_run --

    def test_validate_returns_none_when_inputs_valid(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: IsEntityReference) -> None:
        node.parameter_values["entity_reference"] = "asset://my/thing"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No session connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_empty(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        node.parameter_values["session"] = mock_session

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No entity reference provided" in str(errors[0])

    def test_validate_returns_all_errors_when_both_missing(self, node: IsEntityReference) -> None:
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 2

    # -- process() success path (valid reference) --

    def test_process_outputs_true_for_valid_reference(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is True
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: 'asset://my/thing' is a valid entity reference."
        )

    def test_process_passes_through_session(self, node: IsEntityReference, mock_session: ManagerSession) -> None:
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        assert node.parameter_output_values["session"] is mock_session
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: 'asset://my/thing' is a valid entity reference."
        )

    def test_process_passes_through_entity_reference(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        assert node.parameter_output_values["entity_reference"] == "asset://my/thing"
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: 'asset://my/thing' is a valid entity reference."
        )

    def test_process_calls_manager_with_value(self, node: IsEntityReference, mock_session: ManagerSession) -> None:
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/thing"

        node.process()

        mock_manager.isEntityReferenceString.assert_called_once_with("asset://my/thing")
        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: 'asset://my/thing' is a valid entity reference."
        )

    # -- process() non-reference path --

    def test_process_fails_for_invalid_reference_by_default(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        """With the toggle at its default (on), a non-reference routes the Failed edge."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "not-a-reference"

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is False
        assert node._execution_succeeded is False  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"]
            == "FAILURE: 'not-a-reference' is not a valid entity reference."
        )

    def test_process_succeeds_for_invalid_reference_when_toggle_off(
        self, node: IsEntityReference, mock_session: ManagerSession
    ) -> None:
        """With the toggle off, a non-reference is a normal successful result, not a failure."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "not-a-reference"
        node.parameter_values["fail_if_not_entity_reference"] = False

        node.process()

        assert node.parameter_output_values["is_entity_reference"] is False
        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == (
            "'not-a-reference' is not a valid entity reference. ('Fail if not an entity reference' is off.)"
        )
