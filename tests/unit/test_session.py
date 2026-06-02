# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for session domain logic."""

from __future__ import annotations

import logging
from unittest.mock import Mock

import griptape_nodes_library_openassetio.session as session_mod
import pytest
from griptape_nodes_library_openassetio.session import (
    _SEVERITY_TO_LOG_LEVEL,
    ManagerSession,
    _HostInterface,
    _Logger,
    create_session,
)
from openassetio import Context
from openassetio.hostApi import HostInterface, Manager, ManagerFactory
from openassetio.log import LoggerInterface
from openassetio.pluginSystem import (
    CppPluginSystemManagerImplementationFactory,
    HybridPluginSystemManagerImplementationFactory,
    PythonPluginSystemManagerImplementationFactory,
)


@pytest.mark.usefixtures("griptape_nodes")
class TestLogger:
    """Tests for the _Logger bridge."""

    def test_maps_known_severity_to_python_level(self, caplog: pytest.LogCaptureFixture) -> None:
        oaio_logger = _Logger()
        with caplog.at_level(logging.WARNING):
            oaio_logger.log(LoggerInterface.Severity.kWarning, "watch out")
        assert "watch out" in caplog.text

    def test_maps_info_severity(self, caplog: pytest.LogCaptureFixture) -> None:
        oaio_logger = _Logger()
        with caplog.at_level(logging.INFO):
            oaio_logger.log(LoggerInterface.Severity.kInfo, "informational")
        assert "informational" in caplog.text

    def test_all_severities_have_mappings(self) -> None:
        expected = {
            LoggerInterface.Severity.kDebugApi,
            LoggerInterface.Severity.kDebug,
            LoggerInterface.Severity.kInfo,
            LoggerInterface.Severity.kProgress,
            LoggerInterface.Severity.kWarning,
            LoggerInterface.Severity.kError,
            LoggerInterface.Severity.kCritical,
        }
        assert set(_SEVERITY_TO_LOG_LEVEL.keys()) == expected


@pytest.mark.usefixtures("griptape_nodes")
class TestHostInterface:
    """Tests for the _HostInterface implementation."""

    def test_identifier(self) -> None:
        host = _HostInterface()
        assert host.identifier() == "io.griptape.nodes"

    def test_display_name(self) -> None:
        host = _HostInterface()
        assert host.displayName() == "Griptape Nodes"


@pytest.mark.usefixtures("griptape_nodes")
class TestManagerSession:
    """Tests for the ManagerSession dataclass."""

    def test_bundles_manager_context_host(self) -> None:
        mock_manager = Mock(spec=Manager)
        mock_context = Mock(spec=Context)
        mock_host = Mock(spec=HostInterface)

        session = ManagerSession(manager=mock_manager, context=mock_context, host_interface=mock_host)

        assert session.manager is mock_manager
        assert session.context is mock_context
        assert session.host_interface is mock_host


@pytest.mark.usefixtures("griptape_nodes")
class TestCreateSession:
    """Tests for the create_session function."""

    def test_returns_session_dataclass(self, monkeypatch: pytest.MonkeyPatch) -> None:

        # setup

        mock_manager = Mock(spec=Manager)
        mock_context = Mock(spec=Context)
        mock_manager.createContext.return_value = mock_context
        mock_manager_factory = Mock(spec=ManagerFactory)
        mock_manager_factory.defaultManagerForInterface.return_value = mock_manager

        monkeypatch.setattr(session_mod, "ManagerFactory", mock_manager_factory)
        monkeypatch.setattr(
            session_mod,
            "HybridPluginSystemManagerImplementationFactory",
            Mock(spec=HybridPluginSystemManagerImplementationFactory),
        )
        monkeypatch.setattr(
            session_mod,
            "CppPluginSystemManagerImplementationFactory",
            Mock(spec=CppPluginSystemManagerImplementationFactory),
        )
        monkeypatch.setattr(
            session_mod,
            "PythonPluginSystemManagerImplementationFactory",
            Mock(spec=PythonPluginSystemManagerImplementationFactory),
        )

        # action

        session = create_session()

        # confirm

        assert isinstance(session, ManagerSession)
        assert session.manager is mock_manager
        assert session.context is mock_context
        assert isinstance(session.host_interface, _HostInterface)

    def test_uses_hybrid_factory_with_cpp_first(self, monkeypatch: pytest.MonkeyPatch) -> None:

        # setup

        mock_manager = Mock(spec=Manager)
        mock_manager_factory = Mock(spec=ManagerFactory)
        mock_manager_factory.defaultManagerForInterface.return_value = mock_manager
        mock_cpp_factory_cls = Mock(spec=CppPluginSystemManagerImplementationFactory)
        mock_py_factory_cls = Mock(spec=PythonPluginSystemManagerImplementationFactory)
        mock_hybrid_factory_cls = Mock(spec=HybridPluginSystemManagerImplementationFactory)

        monkeypatch.setattr(session_mod, "ManagerFactory", mock_manager_factory)
        monkeypatch.setattr(session_mod, "CppPluginSystemManagerImplementationFactory", mock_cpp_factory_cls)
        monkeypatch.setattr(session_mod, "PythonPluginSystemManagerImplementationFactory", mock_py_factory_cls)
        monkeypatch.setattr(
            session_mod,
            "HybridPluginSystemManagerImplementationFactory",
            mock_hybrid_factory_cls,
        )

        # action

        create_session()

        # confirm

        oaio_logger = mock_cpp_factory_cls.call_args[0][0]
        assert isinstance(oaio_logger, _Logger)

        mock_cpp_factory_cls.assert_called_once_with(oaio_logger)
        mock_py_factory_cls.assert_called_once_with(oaio_logger)
        mock_hybrid_factory_cls.assert_called_once_with(
            [mock_cpp_factory_cls.return_value, mock_py_factory_cls.return_value],
            oaio_logger,
        )

        host = mock_manager_factory.defaultManagerForInterface.call_args[0][0]
        assert isinstance(host, _HostInterface)
        mock_manager_factory.defaultManagerForInterface.assert_called_once_with(
            host, mock_hybrid_factory_cls.return_value, oaio_logger
        )

    def test_raises_when_no_default_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:

        # setup

        mock_manager_factory = Mock(spec=ManagerFactory)
        mock_manager_factory.defaultManagerForInterface.return_value = None

        monkeypatch.setattr(session_mod, "ManagerFactory", mock_manager_factory)
        monkeypatch.setattr(
            session_mod,
            "HybridPluginSystemManagerImplementationFactory",
            Mock(spec=HybridPluginSystemManagerImplementationFactory),
        )
        monkeypatch.setattr(
            session_mod,
            "CppPluginSystemManagerImplementationFactory",
            Mock(spec=CppPluginSystemManagerImplementationFactory),
        )
        monkeypatch.setattr(
            session_mod,
            "PythonPluginSystemManagerImplementationFactory",
            Mock(spec=PythonPluginSystemManagerImplementationFactory),
        )

        # action / confirm

        with pytest.raises(RuntimeError, match="OPENASSETIO_DEFAULT_CONFIG"):
            create_session()
