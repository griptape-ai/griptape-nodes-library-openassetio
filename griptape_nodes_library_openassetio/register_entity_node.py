# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""RegisterEntity node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.preflight_entity_node import PUBLISHING_ACCESS_BY_LABEL
from griptape_nodes_library_openassetio.register_entity import register_entity
from griptape_nodes_library_openassetio.session import ManagerSession


class RegisterEntity(SuccessFailureNode):
    """Register an entity to finalise publication.

    Calls ``manager.register()`` with the working reference obtained from a prior
    ``PreflightEntity`` node. Outputs the final entity reference that identifies the
    published data.

    The session is passed through for downstream chaining.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Register an entity to finalise publication",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        self.add_parameter(
            Parameter(
                name="session",
                input_types=["ManagerSession"],
                output_type="ManagerSession",
                tooltip="Session from an OpenAssetIOSession node",
                allowed_modes={ParameterMode.INPUT, ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="working_reference",
                input_types=["str"],
                tooltip="Working reference from a PreflightEntity node",
                allowed_modes={ParameterMode.INPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="traits_data",
                input_types=["TraitsData"],
                tooltip=(
                    "TraitsData describing the published data. Typically, matches the TraitsData passed to"
                    " PreflightEntity, but with more trait properties now populated."
                ),
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="publishing_access",
                input_types=["str"],
                tooltip="Publishing access mode (must match PreflightEntity)",
                allowed_modes={ParameterMode.INPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="final_reference",
                output_type="str",
                tooltip="Final reference to the published entity",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the registration result",
            result_details_placeholder="Registration result will be shown here.",
        )

    def validate_before_node_run(self) -> list[Exception] | None:
        """Check that required inputs are present before execution.

        :returns: A list of validation errors, or ``None`` if all inputs are valid.
        """
        exceptions: list[Exception] = []
        session = self.get_parameter_value("session")
        session_valid = isinstance(session, ManagerSession)
        if not session_valid:
            exceptions.append(ValueError(f"{self.name}: No session connected"))
        working_reference = self.get_parameter_value("working_reference")
        if not working_reference:
            exceptions.append(ValueError(f"{self.name}: No working reference provided"))
        elif session_valid and not session.manager.isEntityReferenceString(working_reference):
            exceptions.append(ValueError(f"{self.name}: '{working_reference}' is not a valid entity reference"))
        traits_data = self.get_parameter_value("traits_data")
        if traits_data is None:
            exceptions.append(ValueError(f"{self.name}: No traits data connected"))
        access_label = self.get_parameter_value("publishing_access")
        if not access_label:
            exceptions.append(ValueError(f"{self.name}: No publishing access provided"))
        elif access_label not in PUBLISHING_ACCESS_BY_LABEL:
            exceptions.append(ValueError(f"{self.name}: Unknown publishing access {access_label!r}"))
        return exceptions or None

    def process(self) -> None:
        """Register the entity and output the final reference."""
        self._clear_execution_status()

        session: ManagerSession = self.get_parameter_value("session")
        working_reference: str = self.get_parameter_value("working_reference")
        traits_data = self.get_parameter_value("traits_data")
        access_label: str = self.get_parameter_value("publishing_access")
        # Safe to index directly — validate_before_node_run pre-validates the label.
        access = PUBLISHING_ACCESS_BY_LABEL[access_label]

        try:
            final_reference = register_entity(session, working_reference, traits_data, access)
        except OpenAssetIOException as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        self.parameter_output_values["final_reference"] = final_reference
        self.parameter_output_values["session"] = session

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Registered {final_reference}",
        )
