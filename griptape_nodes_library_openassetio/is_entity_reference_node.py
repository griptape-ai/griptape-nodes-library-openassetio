# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""IsEntityReference node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode

from griptape_nodes_library_openassetio.session import ManagerSession


class IsEntityReference(SuccessFailureNode):
    """Test whether a string is a valid entity reference for the connected manager.

    Takes a string and an OpenAssetIO session, and outputs a boolean indicating whether
    the manager recognises the string as an entity reference. This is a format check
    only — it does not verify that the entity exists.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": ("Test whether a string is a valid entity reference for the connected manager"),
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        self.add_parameter(
            Parameter(
                name="session",
                input_types=["ManagerSession"],
                tooltip="Session from an OpenAssetIOSession node",
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="entity_reference",
                type="str",
                default_value="",
                tooltip="String to test as an entity reference",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="is_entity_reference",
                output_type="bool",
                tooltip="Whether the string is a valid entity reference for the configured manager",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the entity reference check",
            result_details_placeholder="Entity reference check status will be shown here.",
        )

    def process(self) -> None:
        """Check whether the input string is a valid entity reference."""
        self._clear_execution_status()

        session: ManagerSession | None = self.parameter_values.get("session")
        if not isinstance(session, ManagerSession):
            self._set_status_results(
                was_successful=False,
                result_details="FAILURE: No session connected",
            )
            self._handle_failure_exception(ValueError("No session connected. Connect an OpenAssetIOSession node"))
            return

        value: str | None = self.parameter_values.get("entity_reference")
        if not value:
            self._set_status_results(
                was_successful=False,
                result_details="FAILURE: No entity reference provided",
            )
            self._handle_failure_exception(ValueError("No entity reference provided to check"))
            return

        result = session.manager.isEntityReferenceString(value)
        self.parameter_output_values["is_entity_reference"] = result

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: '{value}' is {'a valid' if result else 'not a valid'} entity reference",
        )
