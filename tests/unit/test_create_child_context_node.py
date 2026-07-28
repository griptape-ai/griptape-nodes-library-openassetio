# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the CreateChildContext node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.create_child_context_node as node_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes_library_openassetio.create_child_context import create_child_context
from griptape_nodes_library_openassetio.create_child_context_node import CreateChildContext
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes_library_openassetio.session import ManagerSession


@pytest.mark.usefixtures("griptape_nodes")
class TestCreateChildContextStructure:
    """Tests for the CreateChildContext node parameter structure."""

    @pytest.fixture
    def node(self) -> CreateChildContext:
        """Create a fresh CreateChildContext node."""
        return CreateChildContext(name="test_child_ctx")

    def test_is_data_node(self, node: CreateChildContext) -> None:
        """CreateChildContext should extend DataNode."""
        assert isinstance(node, DataNode)

    def test_has_session_input_parameter(self, node: CreateChildContext) -> None:
        """Session input should be INPUT-only (value is mutated, not passed through)."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.input_types == ["ManagerSession"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_session_input_is_not_serializable(self, node: CreateChildContext) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("session")
        assert param is not None
        assert param.serializable is False

    def test_has_child_session_output_parameter(self, node: CreateChildContext) -> None:
        """Child session output should be OUTPUT-only (new derived value)."""
        param = node.get_parameter_by_name("child_session")
        assert param is not None
        assert param.output_type == "ManagerSession"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_child_session_output_is_not_serializable(self, node: CreateChildContext) -> None:
        """ManagerSession is not JSON-serializable."""
        param = node.get_parameter_by_name("child_session")
        assert param is not None
        assert param.serializable is False

    def test_has_locale_parameter(self, node: CreateChildContext) -> None:
        """Locale should be INPUT-only for wiring from Traits."""
        param = node.get_parameter_by_name("locale")
        assert param is not None
        assert param.input_types == ["TraitsData"]
        assert param.allowed_modes == {ParameterMode.INPUT}

    def test_locale_parameter_is_not_serializable(self, node: CreateChildContext) -> None:
        """TraitsData is not JSON-serializable."""
        param = node.get_parameter_by_name("locale")
        assert param is not None
        assert param.serializable is False

    def test_default_metadata(self, node: CreateChildContext) -> None:
        """Node should have the OpenAssetIO category."""
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        """Passing metadata should merge with the default node metadata."""
        node = CreateChildContext(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"


@pytest.mark.usefixtures("griptape_nodes")
class TestCreateChildContextValidation:
    """Tests for CreateChildContext validate_before_node_run."""

    @pytest.fixture
    def node(self) -> CreateChildContext:
        """Create a fresh CreateChildContext node."""
        return CreateChildContext(name="test_child_ctx_val")

    def test_validate_returns_none_when_session_present(
        self, node: CreateChildContext, mock_session: ManagerSession
    ) -> None:
        node.parameter_values["session"] = mock_session

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_session_missing(self, node: CreateChildContext) -> None:
        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert str(errors[0]) == "test_child_ctx_val: No session connected"


@pytest.mark.usefixtures("griptape_nodes")
class TestCreateChildContextProcess:
    """Tests for the CreateChildContext process() method."""

    @pytest.fixture
    def node(self) -> CreateChildContext:
        """Create a fresh CreateChildContext node."""
        return CreateChildContext(name="test_child_ctx_proc")

    def test_process_delegates_to_create_child_context(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: CreateChildContext,
        make_mock_session: Callable[[], ManagerSession],
    ) -> None:
        """process() should call create_child_context with correct args."""
        new_session = make_mock_session()
        mock_fn = create_autospec(create_child_context, return_value=new_session)
        monkeypatch.setattr(node_mod, "create_child_context", mock_fn)

        session = make_mock_session()
        locale = Mock(spec=TraitsData)
        node.parameter_values["session"] = session
        node.parameter_values["locale"] = locale

        node.process()

        mock_fn.assert_called_once_with(session, locale)

    def test_process_passes_none_locale_when_not_connected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: CreateChildContext,
        make_mock_session: Callable[[], ManagerSession],
    ) -> None:
        """process() should pass None locale when locale is not connected."""
        new_session = make_mock_session()
        mock_fn = create_autospec(create_child_context, return_value=new_session)
        monkeypatch.setattr(node_mod, "create_child_context", mock_fn)

        session = make_mock_session()
        node.parameter_values["session"] = session

        node.process()

        mock_fn.assert_called_once_with(session, None)

    def test_process_outputs_new_session_as_child_session(
        self,
        monkeypatch: pytest.MonkeyPatch,
        node: CreateChildContext,
        make_mock_session: Callable[[], ManagerSession],
    ) -> None:
        """process() should output the new session under child_session."""
        new_session = make_mock_session()
        mock_fn = create_autospec(create_child_context, return_value=new_session)
        monkeypatch.setattr(node_mod, "create_child_context", mock_fn)

        node.parameter_values["session"] = make_mock_session()
        node.parameter_values["locale"] = Mock(spec=TraitsData)

        node.process()

        assert node.parameter_output_values["child_session"] is new_session
