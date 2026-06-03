# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""OpenAssetIO session creation and supporting types."""

from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING, override

from openassetio.hostApi import HostInterface, Manager, ManagerFactory
from openassetio.log import LoggerInterface
from openassetio.pluginSystem import (
    CppPluginSystemManagerImplementationFactory,
    HybridPluginSystemManagerImplementationFactory,
    PythonPluginSystemManagerImplementationFactory,
)

if TYPE_CHECKING:
    from openassetio import Context

logger = logging.getLogger(__name__)

_SEVERITY_TO_LOG_LEVEL: dict[LoggerInterface.Severity, int] = {
    LoggerInterface.Severity.kDebugApi: logging.DEBUG,
    LoggerInterface.Severity.kDebug: logging.DEBUG,
    LoggerInterface.Severity.kInfo: logging.INFO,
    LoggerInterface.Severity.kProgress: logging.INFO,
    LoggerInterface.Severity.kWarning: logging.WARNING,
    LoggerInterface.Severity.kError: logging.ERROR,
    LoggerInterface.Severity.kCritical: logging.CRITICAL,
}


@dataclasses.dataclass
class ManagerSession:
    """Bundles the OpenAssetIO Manager, Context, and HostInterface.

    Downstream nodes receive this single object via a connection rather than three
    separate wires. Access individual components via attributes: ``session.manager``,
    ``session.context``, ``session.host_interface``.
    """

    manager: Manager
    context: Context
    host_interface: HostInterface


class _Logger(LoggerInterface):
    """Bridges OpenAssetIO logging to Python's :mod:`logging`."""

    @override
    def log(
        self,
        severity: LoggerInterface.Severity,
        message: str,
    ) -> None:
        level = _SEVERITY_TO_LOG_LEVEL.get(severity, logging.DEBUG)
        logger.log(level, message)


class _HostInterface(HostInterface):
    """OpenAssetIO host interface for Griptape Nodes."""

    @override
    def identifier(self) -> str:
        return "io.griptape.nodes"

    @override
    def displayName(self) -> str:
        return "Griptape Nodes"


def create_session() -> ManagerSession:
    """Create an OpenAssetIO session using the default manager configuration.

    Reads the ``OPENASSETIO_DEFAULT_CONFIG`` environment variable to locate the manager
    configuration via ``ManagerFactory.defaultManagerForInterface``.

    :returns: A :class:`ManagerSession` bundling the Manager, Context, and
        HostInterface.
    """
    oaio_logger = _Logger()
    impl_factory = HybridPluginSystemManagerImplementationFactory(
        [
            CppPluginSystemManagerImplementationFactory(oaio_logger),
            PythonPluginSystemManagerImplementationFactory(oaio_logger),
        ],
        oaio_logger,
    )
    host_interface = _HostInterface()
    manager = ManagerFactory.defaultManagerForInterface(host_interface, impl_factory, oaio_logger)
    if manager is None:
        msg = (
            "No default manager configured. "
            "Set the OPENASSETIO_DEFAULT_CONFIG environment variable to a valid config file."
        )
        raise RuntimeError(msg)
    context = manager.createContext()
    return ManagerSession(
        manager=manager,
        context=context,
        host_interface=host_interface,
    )
