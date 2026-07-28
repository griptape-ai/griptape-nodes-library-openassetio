# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the PreflightEntity node."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.preflight_entity_node as preflight_node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.preflight_entity import preflight_entity
from griptape_nodes_library_openassetio.preflight_entity_node import PreflightEntity
from openassetio.access import PublishingAccess
from openassetio.errors import OpenAssetIOException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestPreflightEntityStructure:
    """Tests for the PreflightEntity node parameter structure."""

    @pytest.fixture
    def node(self) -> PreflightEntity:
        """Create a fresh PreflightEntity node."""
        return PreflightEntity(name="test_preflight")

    def test_is_success_failure_node(self, node: PreflightEntity) -> None:
        """PreflightEntity should extend SuccessFailureNode."""
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_parameter_with_pass_through(self, node: PreflightEntity) -> None:
        """Session should be INPUT+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: PreflightEntity) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_parameter(self, node: PreflightEntity) -> None:
        """entity_reference should be INPUT+PROPERTY for user entry or wiring."""
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_has_traits_data_parameter_with_pass_through(self, node: PreflightEntity) -> None:
        """traits_data should be INPUT+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("traits_data")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.output_type == "TraitsData"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_has_publishing_access_parameter(self, node: PreflightEntity) -> None:
        """publishing_access should be a PROPERTY+OUTPUT dropdown."""
        param = node.get_parameter_by_name("publishing_access")
        assert param is not None
        assert param.type == "str"
        assert param.default_value == "Write"
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.PROPERTY, ParameterMode.OUTPUT}

    def test_publishing_access_has_options(self, node: PreflightEntity) -> None:
        """publishing_access should have dropdown choices."""
        param = node.get_parameter_by_name("publishing_access")
        assert param is not None
        ui_opts = param.ui_options
        # Options trait stores choices under simple_dropdown.
        assert "simple_dropdown" in ui_opts
        choices = ui_opts["simple_dropdown"]
        assert "Write" in choices
        assert "Create Related" in choices

    def test_has_working_reference_output(self, node: PreflightEntity) -> None:
        """working_reference should be OUTPUT-only."""
        param = node.get_parameter_by_name("working_reference")
        assert param is not None
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_default_metadata(self, node: PreflightEntity) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        """Passing metadata should merge with the default node metadata."""
        node = PreflightEntity(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"


@pytest.mark.usefixtures("griptape_nodes")
class TestPreflightEntityValidation:
    """Tests for PreflightEntity validate_before_node_run."""

    @pytest.fixture
    def node(self) -> PreflightEntity:
        """Create a fresh PreflightEntity node."""
        return PreflightEntity(name="test_preflight_val")

    def test_validate_returns_none_when_inputs_valid(self, node: PreflightEntity, mock_session: ManagerSession) -> None:
        """validate_before_node_run should pass when all inputs present."""
        cast("Mock", mock_session.manager).isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: PreflightEntity) -> None:
        """validate_before_node_run should fail when session is missing."""
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No session connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_missing(
        self, node: PreflightEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when entity_reference is empty."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No entity reference provided" in str(errors[0])

    def test_validate_returns_error_when_traits_data_missing(
        self, node: PreflightEntity, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when traits_data is missing."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No traits data connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_invalid_format(
        self, node: PreflightEntity, mock_session: ManagerSession
    ) -> None:
        """A syntactically invalid reference is a validation error."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "not-a-reference"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "'not-a-reference' is not a valid entity reference" in str(errors[0])

    def test_validate_returns_all_errors_when_all_missing(self, node: PreflightEntity) -> None:
        """validate_before_node_run should return all errors at once."""
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 3


@pytest.mark.usefixtures("griptape_nodes")
class TestPreflightEntityProcess:
    """Tests for the PreflightEntity process() method."""

    @pytest.fixture
    def node(self) -> PreflightEntity:
        """Create a fresh PreflightEntity node."""
        return PreflightEntity(name="test_preflight_proc")

    def test_process_delegates_to_preflight_entity(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should call preflight_entity with correct args."""
        mock_preflight = create_autospec(preflight_entity, return_value="asset://working/ref")
        monkeypatch.setattr(preflight_node_mod, "preflight_entity", mock_preflight)

        input_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = input_td

        node.process()

        mock_preflight.assert_called_once_with(mock_session, "asset://my/entity", input_td, PublishingAccess.kWrite)

    def test_process_uses_default_write_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() uses kWrite when publishing_access dropdown is at its default value.

        The ``publishing_access`` parameter stores its default in
        ``Parameter.default_value``, not in ``parameter_values``.
        ``get_parameter_value()`` must return the stored default so the correct access
        mode is used when the user has not changed the dropdown.
        """
        mock_preflight = create_autospec(preflight_entity, return_value="asset://working/ref")
        monkeypatch.setattr(preflight_node_mod, "preflight_entity", mock_preflight)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        # publishing_access NOT set — process() must read the default from the parameter.

        node.process()

        call_args = mock_preflight.call_args[0]
        assert call_args[3] == PublishingAccess.kWrite

    def test_process_uses_create_related_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass kCreateRelated when selected."""
        mock_preflight = create_autospec(preflight_entity, return_value="asset://working/ref")
        monkeypatch.setattr(preflight_node_mod, "preflight_entity", mock_preflight)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.set_parameter_value("publishing_access", "Create Related")

        node.process()

        call_args = mock_preflight.call_args[0]
        assert call_args[3] == PublishingAccess.kCreateRelated

    def test_process_outputs_working_reference(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should output the working reference."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, return_value="asset://working/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["working_reference"] == "asset://working/ref"

    def test_process_passes_through_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the session."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, return_value="asset://working/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["session"] is mock_session

    def test_process_passes_through_traits_data(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through traits_data unchanged."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, return_value="asset://working/ref"),
        )

        input_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = input_td

        node.process()

        assert node.parameter_output_values["traits_data"] is input_td

    def test_process_passes_through_publishing_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through publishing_access for RegisterEntity."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, return_value="asset://working/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)
        node.set_parameter_value("publishing_access", "Create Related")

        node.process()

        assert node.parameter_output_values["publishing_access"] == "Create Related"

    def test_process_sets_success_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with the entity reference."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, return_value="asset://working/ref"),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Preflighted asset://my/entity"

    def test_process_fails_on_openassetio_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: PreflightEntity,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report failure on OpenAssetIO exceptions."""
        monkeypatch.setattr(
            preflight_node_mod,
            "preflight_entity",
            create_autospec(preflight_entity, side_effect=OpenAssetIOException("Preflight failed")),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["traits_data"] = Mock(spec=TraitsData)

        with pytest.raises(OpenAssetIOException, match="Preflight failed"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Preflight failed"
