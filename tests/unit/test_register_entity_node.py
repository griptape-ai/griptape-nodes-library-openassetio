# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the RegisterEntity node."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.register_entity_node as register_node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.register_entity import register_entity
from griptape_nodes_library_openassetio.register_entity_node import RegisterEntity
from openassetio.access import PublishingAccess
from openassetio.errors import OpenAssetIOException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestRegisterEntityStructure:
    """Tests for the RegisterEntity node parameter structure."""

    @pytest.fixture
    def node(self) -> RegisterEntity:
        """Create a fresh RegisterEntity node."""
        return RegisterEntity(name="test_register")

    def test_is_success_failure_node(self, node: RegisterEntity) -> None:
        """RegisterEntity should extend SuccessFailureNode."""
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_parameter_with_pass_through(self, node: RegisterEntity) -> None:
        """Session should be INPUT+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: RegisterEntity) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_working_reference_parameter(self, node: RegisterEntity) -> None:
        """working_reference should be INPUT-only."""
        param = node.get_parameter_by_name("working_reference")
        assert param is not None
        assert param.input_types == ["str"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_has_traits_data_parameter(self, node: RegisterEntity) -> None:
        """traits_data should be INPUT-only (terminal — consumed, not passed through)."""
        param = node.get_parameter_by_name("traits_data")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_has_publishing_access_parameter(self, node: RegisterEntity) -> None:
        """publishing_access should be INPUT-only (receives from PreflightEntity)."""
        param = node.get_parameter_by_name("publishing_access")
        assert param is not None
        assert param.input_types == ["str"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_has_final_reference_output(self, node: RegisterEntity) -> None:
        """final_reference should be OUTPUT-only."""
        param = node.get_parameter_by_name("final_reference")
        assert param is not None
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_default_metadata(self, node: RegisterEntity) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        """Passing metadata should merge with the default node metadata."""
        node = RegisterEntity(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"


@pytest.mark.usefixtures("griptape_nodes")
class TestRegisterEntityValidation:
    """Tests for RegisterEntity validate_before_node_run."""

    @pytest.fixture
    def node(self) -> RegisterEntity:
        """Create a fresh RegisterEntity node."""
        return RegisterEntity(name="test_register_val")

    def test_validate_returns_none_when_inputs_valid(self, node: RegisterEntity, mock_session: ManagerSession) -> None:
        """validate_before_node_run should pass when all inputs present."""
        cast("Mock", mock_session.manager).isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: RegisterEntity) -> None:
        """validate_before_node_run should fail when session is missing."""
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No session connected" in str(errors[0])

    def test_validate_returns_error_when_working_reference_missing(
        self, node: RegisterEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when working_reference is empty."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No working reference provided" in str(errors[0])

    def test_validate_returns_error_when_traits_data_missing(
        self, node: RegisterEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when traits_data is missing."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["publishing_access"] = "Write"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No traits data connected" in str(errors[0])

    def test_validate_returns_error_when_publishing_access_missing(
        self, node: RegisterEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when publishing_access is empty."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No publishing access provided" in str(errors[0])

    def test_validate_returns_error_when_publishing_access_unknown(
        self, node: RegisterEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when publishing_access is not a known label."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "InvalidMode"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "Unknown publishing access 'InvalidMode'" in str(errors[0])

    def test_validate_returns_error_when_working_reference_invalid_format(
        self, node: RegisterEntity, mock_session: ManagerSession
    ) -> None:
        """A syntactically invalid working reference is a validation error."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "not-a-reference"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "'not-a-reference' is not a valid entity reference" in str(errors[0])

    def test_validate_returns_all_errors_when_all_missing(self, node: RegisterEntity) -> None:
        """validate_before_node_run should return all errors at once."""
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 4


@pytest.mark.usefixtures("griptape_nodes")
class TestRegisterEntityProcess:
    """Tests for the RegisterEntity process() method."""

    @pytest.fixture
    def node(self) -> RegisterEntity:
        """Create a fresh RegisterEntity node."""
        return RegisterEntity(name="test_register_proc")

    def test_process_delegates_to_register_entity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should call register_entity with correct args."""
        mock_register = create_autospec(register_entity, return_value="asset://final/ref")
        monkeypatch.setattr(register_node_mod, "register_entity", mock_register)

        input_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = input_td
        node.parameter_values["publishing_access"] = "Write"

        node.process()

        mock_register.assert_called_once_with(mock_session, "asset://working/ref", input_td, PublishingAccess.kWrite)

    def test_process_uses_create_related_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass kCreateRelated when publishing_access says so."""
        mock_register = create_autospec(register_entity, return_value="asset://final/ref")
        monkeypatch.setattr(register_node_mod, "register_entity", mock_register)

        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Create Related"

        node.process()

        call_args = mock_register.call_args[0]
        assert call_args[3] == PublishingAccess.kCreateRelated

    def test_process_outputs_final_reference(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should output the final reference."""
        monkeypatch.setattr(
            register_node_mod,
            "register_entity",
            create_autospec(register_entity, return_value="asset://final/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        node.process()

        assert node.parameter_output_values["final_reference"] == "asset://final/ref"

    def test_process_passes_through_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the session."""
        monkeypatch.setattr(
            register_node_mod,
            "register_entity",
            create_autospec(register_entity, return_value="asset://final/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        node.process()

        assert node.parameter_output_values["session"] is mock_session

    def test_process_sets_success_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with the final reference."""
        monkeypatch.setattr(
            register_node_mod,
            "register_entity",
            create_autospec(register_entity, return_value="asset://final/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Registered asset://final/ref"

    def test_process_fails_on_openassetio_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RegisterEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report failure on OpenAssetIO exceptions."""
        monkeypatch.setattr(
            register_node_mod,
            "register_entity",
            create_autospec(register_entity, side_effect=OpenAssetIOException("Registration failed")),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["working_reference"] = "asset://working/ref"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["publishing_access"] = "Write"

        with pytest.raises(OpenAssetIOException, match="Registration failed"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Registration failed"
