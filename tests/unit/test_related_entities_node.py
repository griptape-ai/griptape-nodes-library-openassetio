# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the RelatedEntities node."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.related_entities_node as node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.related_entities import (
    RelationshipCriteria,
    get_related_entities,
)
from griptape_nodes_library_openassetio.related_entities_node import RelatedEntities
from openassetio.access import RelationsAccess
from openassetio.errors import BatchElementError, BatchElementException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestRelatedEntitiesStructure:
    """Tests for the RelatedEntities node parameter structure."""

    @pytest.fixture
    def node(self) -> RelatedEntities:
        """Create a fresh RelatedEntities node."""
        return RelatedEntities(name="test_gwr")

    def test_is_success_failure_node(self, node: RelatedEntities) -> None:
        """RelatedEntities should extend SuccessFailureNode."""
        assert isinstance(node, SuccessFailureNode)

    def test_has_session_parameter_with_pass_through(self, node: RelatedEntities) -> None:
        """Session should be INPUT+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.OUTPUT}

    def test_session_parameter_is_not_serializable(self, node: RelatedEntities) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_entity_reference_parameter_with_pass_through(self, node: RelatedEntities) -> None:
        """entity_reference should be INPUT+PROPERTY+OUTPUT for pass-through."""
        param = node.get_parameter_by_name("entity_reference")
        assert param is not None
        assert param.type == "str"
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT}

    def test_has_relationship_traits_data_parameter(self, node: RelatedEntities) -> None:
        """relationship_traits_data should be INPUT-only, accepting TraitsData."""
        param = node.get_parameter_by_name("relationship_traits_data")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_relationship_traits_data_is_not_serializable(self, node: RelatedEntities) -> None:
        """TraitsData is not JSON-serializable."""
        param = node.get_parameter_by_name("relationship_traits_data")
        assert param is not None
        assert param.serializable is False

    def test_has_result_traits_data_parameter(self, node: RelatedEntities) -> None:
        """result_traits_data should be INPUT-only, accepting TraitsData."""
        param = node.get_parameter_by_name("result_traits_data")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_result_traits_data_is_not_serializable(self, node: RelatedEntities) -> None:
        """TraitsData is not JSON-serializable."""
        param = node.get_parameter_by_name("result_traits_data")
        assert param is not None
        assert param.serializable is False

    def test_has_access_parameter(self, node: RelatedEntities) -> None:
        """Access should be a PROPERTY dropdown defaulting to Read."""
        param = node.get_parameter_by_name("access")
        assert param is not None
        assert param.type == "str"
        assert param.default_value == "Read"
        assert param.allowed_modes == {ParameterMode.PROPERTY}

    def test_access_parameter_has_options(self, node: RelatedEntities) -> None:
        """Access should have Options trait with Read, Write, and Create Related choices."""
        param = node.get_parameter_by_name("access")
        assert param is not None
        ui_opts = param.ui_options
        assert "simple_dropdown" in ui_opts
        choices = ui_opts["simple_dropdown"]
        assert "Read" in choices
        assert "Write" in choices
        assert "Create Related" in choices

    def test_has_max_results_parameter(self, node: RelatedEntities) -> None:
        """max_results should be a PROPERTY int defaulting to 200."""
        param = node.get_parameter_by_name("max_results")
        assert param is not None
        assert param.type == "int"
        assert param.default_value == 200
        assert param.allowed_modes == {ParameterMode.PROPERTY}

    def test_has_related_references_output(self, node: RelatedEntities) -> None:
        """related_references should be OUTPUT-only list."""
        param = node.get_parameter_by_name("related_references")
        assert param is not None
        assert param.output_type == "list"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_default_metadata(self, node: RelatedEntities) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"


@pytest.mark.usefixtures("griptape_nodes")
class TestRelatedEntitiesValidation:
    """Tests for RelatedEntities validate_before_node_run."""

    @pytest.fixture
    def node(self) -> RelatedEntities:
        """Create a fresh RelatedEntities node."""
        return RelatedEntities(name="test_gwr_val")

    def test_validate_returns_none_when_inputs_valid(self, node: RelatedEntities, mock_session: ManagerSession) -> None:
        """validate_before_node_run should pass when all inputs present."""
        cast("Mock", mock_session.manager).isEntityReferenceString.return_value = True
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: RelatedEntities) -> None:
        """validate_before_node_run should fail when session is missing."""
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No session connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_missing(
        self, node: RelatedEntities, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when entity_reference is empty."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No entity reference provided" in str(errors[0])

    def test_validate_returns_error_when_relationship_traits_data_missing(
        self, node: RelatedEntities, mock_session: ManagerSession
    ) -> None:
        """validate_before_node_run should fail when relationship_traits_data is missing."""
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No relationship traits data connected" in str(errors[0])

    def test_validate_returns_error_when_entity_reference_invalid_format(
        self, node: RelatedEntities, mock_session: ManagerSession
    ) -> None:
        """A syntactically invalid reference is a validation error."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.isEntityReferenceString.return_value = False
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "not-a-reference"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "'not-a-reference' is not a valid entity reference" in str(errors[0])

    def test_validate_returns_all_errors_when_all_missing(self, node: RelatedEntities) -> None:
        """validate_before_node_run should return all errors at once."""
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 3


@pytest.mark.usefixtures("griptape_nodes")
class TestRelatedEntitiesProcess:
    """Tests for the RelatedEntities process() method."""

    @pytest.fixture
    def node(self) -> RelatedEntities:
        """Create a fresh RelatedEntities node."""
        return RelatedEntities(name="test_gwr_proc")

    def test_process_delegates_to_get_related_entities(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should call get_related_entities with correct arguments."""
        mock_gre = create_autospec(get_related_entities, return_value=["asset://child/1"])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        relationship_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        expected_criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td,
            result_traits_data=None,
            max_results=200,
        )
        mock_gre.assert_called_once_with(mock_session, "asset://my/entity", expected_criteria, RelationsAccess.kRead)

    def test_process_uses_default_read_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() uses kRead when the access dropdown is at its default value.

        The ``access`` parameter stores its default in ``Parameter.default_value``, not
        in ``parameter_values``. ``get_parameter_value()`` must return the stored
        default so the correct access mode is used when the user has not changed the
        dropdown.
        """
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)
        # access NOT set — process() must read the default from the parameter definition.

        node.process()

        call_args = mock_gre.call_args[0]
        assert call_args[3] == RelationsAccess.kRead

    def test_process_passes_result_traits_data_when_provided(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass result_traits_data when connected."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        result_td = Mock(spec=TraitsData)
        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)
        node.parameter_values["result_traits_data"] = result_td

        node.process()

        criteria = mock_gre.call_args[0][2]
        assert criteria.result_traits_data is result_td

    def test_process_uses_write_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass kWrite when access is 'Write'."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)
        node.set_parameter_value("access", "Write")

        node.process()

        assert mock_gre.call_args[0][3] == RelationsAccess.kWrite

    def test_process_uses_create_related_access(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass kCreateRelated when access is 'Create Related'."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)
        node.set_parameter_value("access", "Create Related")

        node.process()

        assert mock_gre.call_args[0][3] == RelationsAccess.kCreateRelated

    def test_process_passes_max_results(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass max_results to the business logic."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)
        node.set_parameter_value("max_results", 50)

        node.process()

        criteria = mock_gre.call_args[0][2]
        assert criteria.max_results == 50

    def test_process_outputs_related_references(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should output the list of related references."""
        mock_gre = create_autospec(get_related_entities, return_value=["asset://child/1", "asset://child/2"])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["related_references"] == ["asset://child/1", "asset://child/2"]

    def test_process_passes_through_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the session."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["session"] is mock_session

    def test_process_passes_through_entity_reference(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should pass through the entity reference."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["entity_reference"] == "asset://my/entity"

    def test_process_sets_success_status_plural(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with plural 'entities' for multiple results."""
        mock_gre = create_autospec(get_related_entities, return_value=["asset://child/1", "asset://child/2"])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: Found 2 related entities for asset://my/entity"
        )

    def test_process_sets_success_status_singular(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with singular 'entity' for one result."""
        mock_gre = create_autospec(get_related_entities, return_value=["asset://child/1"])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Found 1 related entity for asset://my/entity"

    def test_process_sets_success_status_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report success with plural 'entities' for zero results."""
        mock_gre = create_autospec(get_related_entities, return_value=[])
        monkeypatch.setattr(node_mod, "get_related_entities", mock_gre)

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert (
            node.parameter_output_values["result_details"] == "SUCCESS: Found 0 related entities for asset://my/entity"
        )

    def test_process_fails_on_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: RelatedEntities,
        mock_session: ManagerSession,
    ) -> None:
        """process() should report failure on OpenAssetIO exceptions."""
        error = BatchElementException(0, Mock(spec=BatchElementError), "Relationship query failed")
        monkeypatch.setattr(
            node_mod,
            "get_related_entities",
            create_autospec(get_related_entities, side_effect=error),
        )

        node.parameter_values["session"] = mock_session
        node.parameter_values["entity_reference"] = "asset://my/entity"
        node.parameter_values["relationship_traits_data"] = Mock(spec=TraitsData)

        with pytest.raises(BatchElementException, match="Relationship query failed"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Relationship query failed"
