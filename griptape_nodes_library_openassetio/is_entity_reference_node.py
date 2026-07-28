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
                output_type="ManagerSession",
                tooltip="Session from an OpenAssetIOSession node",
                allowed_modes={ParameterMode.INPUT, ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="entity_reference",
                type="str",
                output_type="str",
                default_value="",
                tooltip="String to test as an entity reference",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
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
        self.add_parameter(
            Parameter(
                name="fail_if_not_entity_reference",
                input_types=["bool"],
                type="bool",
                output_type="bool",
                default_value=True,
                tooltip=(
                    "When on, the node routes through the Failed control edge if the string is not a valid entity"
                    " reference - useful for guarding a graph against bad input. When off, a non-reference is treated"
                    " as a normal successful result; read the boolean output to branch instead."
                ),
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                ui_options={"display_name": "Fail if not an entity reference"},
            )
        )

        # MUST be the last call in __init__ (SuccessFailureNode contract).
        self._create_status_parameters(
            result_details_tooltip="Details about the entity reference check",
            result_details_placeholder="Check result will be shown here.",
        )

    def validate_before_node_run(self) -> list[Exception] | None:
        """Check that required inputs are present before execution.

        :returns: A list of validation errors, or ``None`` if all inputs are valid.
        """
        exceptions: list[Exception] = []
        session = self.get_parameter_value("session")
        if not isinstance(session, ManagerSession):
            exceptions.append(ValueError(f"{self.name}: No session connected"))
        value = self.get_parameter_value("entity_reference")
        if not value:
            exceptions.append(ValueError(f"{self.name}: No entity reference provided"))
        return exceptions or None

    def process(self) -> None:
        """Check whether the input string is a valid entity reference.

        The ``is_entity_reference`` boolean and the pass-through outputs are always
        populated. The success/failure status — and therefore which control edge is
        followed — depends on the check result and the ``fail_if_not_entity_reference``
        toggle. A non-reference with the toggle on is a genuine (non-exception) failure,
        so it routes the Failed edge without raising.
        """
        self._clear_execution_status()

        session: ManagerSession = self.get_parameter_value("session")
        value: str = self.get_parameter_value("entity_reference")
        fail_if_not_entity_reference: bool = self.get_parameter_value("fail_if_not_entity_reference")

        result = session.manager.isEntityReferenceString(value)

        self.parameter_output_values["is_entity_reference"] = result
        self.parameter_output_values["session"] = session
        self.parameter_output_values["entity_reference"] = value

        if result:
            self._set_status_results(
                was_successful=True,
                result_details=f"SUCCESS: '{value}' is a valid entity reference.",
            )
            return

        # Not a valid entity reference. This is a legitimate answer, not an exception, so
        # even the failure branch just sets the status (no _handle_failure_exception).
        if fail_if_not_entity_reference:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: '{value}' is not a valid entity reference.",
            )
            return

        self._set_status_results(
            was_successful=True,
            result_details=f"'{value}' is not a valid entity reference. ('Fail if not an entity reference' is off.)",
        )
