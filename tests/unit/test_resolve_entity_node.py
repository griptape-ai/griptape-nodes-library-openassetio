# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the ResolveEntity node."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.resolve_entity_node as resolve_node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from griptape_nodes_library_openassetio.resolve_entity_node import ResolveEntity
from openassetio.access import ResolveAccess
from openassetio.errors import OpenAssetIOException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityStructure:
    """Tests for the ResolveEntity node parameter structure."""

    @pytest.fixture
    def node(self) -> ResolveEntity:
        """Create a fresh ResolveEntity node."""
        return ResolveEntity(name="test_resolve")

    def test_is_success_failure_node(self, node: ResolveEntity) -> None:
        """ResolveEntity should extend SuccessFailureNode."""
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_parameter_with_pass_through(self, node: ResolveEntity) -> None:
        """Session should be INPUT+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: ResolveEntity) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_parameter_with_pass_through(self, node: ResolveEntity) -> None:
        """entity_reference should be INPUT+PROPERTY+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT}

    def test_has_traits_data_in_parameter(self, node: ResolveEntity) -> None:
        """traits_data_in should be INPUT-only, accepting TraitsData."""
        param = node.get_parameter_by_name("traits_data_in")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_has_traits_data_out_parameter(self, node: ResolveEntity) -> None:
        """traits_data_out should be OUTPUT-only."""
        param = node.get_parameter_by_name("traits_data_out")
        assert param is not None
        assert param.output_type == "TraitsData"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_has_access_parameter(self, node: ResolveEntity) -> None:
        """Access should be a PROPERTY dropdown with Read/Manager Driven."""
        param = node.get_parameter_by_name("access")
        assert param is not None
        assert param.type == "str"
        assert param.default_value == "Read"
        assert param.allowed_modes == {ParameterMode.PROPERTY}

    def test_access_parameter_has_options(self, node: ResolveEntity) -> None:
        """Access should have Options trait with Read and Manager Driven choices."""
        param = node.get_parameter_by_name("access")
        assert param is not None
        ui_opts = param.ui_options
        # Options trait stores choices under simple_dropdown.
        assert "simple_dropdown" in ui_opts
        choices = ui_opts["simple_dropdown"]
        assert "Read" in choices
        assert "Manager Driven" in choices

    def test_default_metadata(self, node: ResolveEntity) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityValidation:
    """Tests for ResolveEntity validate_before_node_run."""

    @pytest.fixture
    def node(self) -> ResolveEntity:
        """Create a fresh ResolveEntity node."""
        return ResolveEntity(name="test_resolve_val")

    def test_validate_returns_none_when_inputs_valid(self, node: ResolveEntity, mock_session: ManagerSession) -> None:
        """validate_before_node_run should pass when all inputs present."""
        cast("Mock", mock_session.manager).isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: ResolveEntity) -> None:
        """validate_before_node_run should fail when session is missing."""
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No session connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_missing(
        self, node: ResolveEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when entity_reference is empty."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No entity reference provided" in str(errors[0])

    def test_validate_returns_error_when_traits_data_in_missing(
        self, node: ResolveEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when traits_data_in is missing."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No traits data input connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_invalid_format(
        self, node: ResolveEntity, mock_session: ManagerSession
    ) -> None:
        """A syntactically invalid reference is a validation error."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "not-a-reference"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "'not-a-reference' is not a valid entity reference" in str(errors[0])

    def test_validate_returns_all_errors_when_all_missing(self, node: ResolveEntity) -> None:
        """validate_before_node_run should return all errors at once."""
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 3


@pytest.mark.usefixtures("griptape_nodes")
class TestResolveEntityProcess:
    """Tests for the ResolveEntity process() method."""

    @pytest.fixture
    def node(self) -> ResolveEntity:
        """Create a fresh ResolveEntity node."""
        return ResolveEntity(name="test_resolve_proc")

    def test_process_delegates_to_resolve_entity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should call resolve_entity with session, ref, traits_data, and access."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = set()
        mock_resolve = create_autospec(resolve_entity, return_value=mock_output_td)
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        input_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = input_td

        node.process()

        mock_resolve.assert_called_once_with(mock_session, "asset://my/entity", input_td, ResolveAccess.kRead)

    def test_process_uses_default_read_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() uses kRead when the access dropdown is at its default value.

        The ``access`` parameter stores its default in ``Parameter.default_value``, not
        in ``parameter_values``. ``get_parameter_value()`` must return the stored
        default so the correct access mode is used when the user has not changed the
        dropdown.
        """
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = set()
        mock_resolve = create_autospec(resolve_entity, return_value=mock_output_td)
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)
        # access NOT set — process() must read the default from the parameter definition.

        node.process()

        call_args = mock_resolve.call_args[0]
        assert call_args[3] == ResolveAccess.kRead

    def test_process_uses_manager_driven_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass kManagerDriven when access is 'Manager Driven'."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = set()
        mock_resolve = create_autospec(resolve_entity, return_value=mock_output_td)
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        input_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = input_td
        node.set_parameter_value("access", "Manager Driven")

        node.process()

        call_args = mock_resolve.call_args[0]
        assert call_args[3] == ResolveAccess.kManagerDriven

    def test_process_outputs_traits_data_out(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should output the resolved TraitsData."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = {"test:content.LocatableContent"}
        mock_resolve = create_autospec(resolve_entity, return_value=mock_output_td)
        monkeypatch.setattr(resolve_node_mod, "resolve_entity", mock_resolve)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["traits_data_out"] is mock_output_td

    def test_process_passes_through_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the session."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = set()
        monkeypatch.setattr(
            resolve_node_mod, "resolve_entity", create_autospec(resolve_entity, return_value=mock_output_td)
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["session"] is mock_session

    def test_process_passes_through_entity_reference(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the entity reference."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = set()
        monkeypatch.setattr(
            resolve_node_mod, "resolve_entity", create_autospec(resolve_entity, return_value=mock_output_td)
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["entity_reference"] == "asset://my/entity"

    def test_process_sets_success_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with the entity reference."""
        mock_output_td = Mock(spec=TraitsData)
        mock_output_td.traitSet.return_value = {"test:content.LocatableContent"}
        monkeypatch.setattr(
            resolve_node_mod, "resolve_entity", create_autospec(resolve_entity, return_value=mock_output_td)
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Resolved asset://my/entity"

    def test_process_fails_on_openassetio_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: ResolveEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report failure on OpenAssetIO exceptions."""
        monkeypatch.setattr(
            resolve_node_mod,
            "resolve_entity",
            create_autospec(resolve_entity, side_effect=OpenAssetIOException("Entity not found")),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://missing"
        node.parameter_values["traits_data_in"] = Mock(spec=TraitsData)

        with pytest.raises(OpenAssetIOException, match="Entity not found"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Entity not found"
