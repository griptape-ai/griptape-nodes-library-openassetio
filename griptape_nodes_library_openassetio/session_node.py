# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""OpenAssetIO session node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.session import create_session


class OpenAssetIOSession(SuccessFailureNode):
    """Initialise an OpenAssetIO session and output a bundled session object.

    Uses the OpenAssetIO function ``defaultManagerForInterface``, which reads the
    ``OPENASSETIO_DEFAULT_CONFIG`` environment variable to locate the manager
    configuration. The resulting Manager, Context, and HostInterface are bundled into a
    single :class:`~griptape_nodes_library_openassetio.session.ManagerSession` dataclass
    for downstream nodes.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its output parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Initialise an OpenAssetIO session",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        self.add_parameter(
            Parameter(
                name="session",
                output_type="ManagerSession",
                tooltip="Bundled Manager, Context, and HostInterface for downstream nodes",
                allowed_modes={ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="manager_display_name",
                output_type="str",
                tooltip="Human-readable name of the connected manager",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="manager_identifier",
                output_type="str",
                tooltip="Stable unique identifier of the connected manager",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the session initialisation result",
            result_details_placeholder="Session initialisation status will be shown here.",
        )

    def process(self) -> None:
        """Initialise the OpenAssetIO manager and populate the session output."""
        self._clear_execution_status()

        try:
            session = create_session()
        except (RuntimeError, OpenAssetIOException) as e:
            self._set_status_results(was_successful=False, result_details=f"FAILURE: {e}")
            self._handle_failure_exception(e)
            return

        self.parameter_output_values["session"] = session
        self.parameter_output_values["manager_display_name"] = session.manager.displayName()
        self.parameter_output_values["manager_identifier"] = session.manager.identifier()

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Connected to {session.manager.displayName()}",
        )
