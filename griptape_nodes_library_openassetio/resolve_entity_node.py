# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""ResolveEntity node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes.traits.options import Options
from openassetio.access import ResolveAccess
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from griptape_nodes_library_openassetio.session import ManagerSession


class ResolveEntity(SuccessFailureNode):
    """Resolve an entity reference against the asset manager.

    Takes an entity reference, a ``TraitsData`` describing the traits to resolve, and an
    access mode. Calls ``manager.resolve()`` and outputs the merged ``TraitsData``
    containing both input and resolved property values.

    The ``traits_data_in`` input should come from an upstream ``Traits`` node that
    defines which traits and properties to resolve. The ``access`` dropdown selects the
    resolve access mode: "Read" for normal lookups, "Manager Driven" for
    working-reference resolution during publishing.

    Session and entity_reference are passed through for downstream chaining.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Resolve an entity reference against the asset manager",
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
                default_value="",
                output_type="str",
                tooltip="Entity reference to resolve",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="traits_data_in",
                input_types=["TraitsData"],
                tooltip="TraitsData defining which traits to resolve",
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="access",
                type="str",
                default_value="Read",
                tooltip=(
                    "Resolve access mode. Use Read to request the current value of trait properties. Use Manager Driven"
                    " to request the expected value of trait properties when publishing - e.g. where to place a file."
                    " Manager Driven should only be used when resolving a working reference, provided by the preflight"
                    " step of the publishing process"
                ),
                allowed_modes={ParameterMode.PROPERTY},
                traits={Options(choices=list(_RESOLVE_ACCESS_BY_LABEL.keys()))},
            )
        )
        self.add_parameter(
            Parameter(
                name="traits_data_out",
                output_type="TraitsData",
                tooltip="Resolved TraitsData with merged property values",
                allowed_modes={ParameterMode.OUTPUT},
                serializable=False,
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the resolve operation result",
            result_details_placeholder="Resolve result will be shown here.",
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
        entity_reference = self.get_parameter_value("entity_reference")
        if not entity_reference:
            exceptions.append(ValueError(f"{self.name}: No entity reference provided"))
        elif session_valid and not session.manager.isEntityReferenceString(entity_reference):
            exceptions.append(ValueError(f"{self.name}: '{entity_reference}' is not a valid entity reference"))
        traits_data_in = self.get_parameter_value("traits_data_in")
        if traits_data_in is None:
            exceptions.append(ValueError(f"{self.name}: No traits data input connected"))
        return exceptions or None

    def process(self) -> None:
        """Resolve the entity reference and output the merged TraitsData."""
        self._clear_execution_status()

        session: ManagerSession = self.get_parameter_value("session")
        entity_reference: str = self.get_parameter_value("entity_reference")
        traits_data_in = self.get_parameter_value("traits_data_in")
        access_label: str = self.get_parameter_value("access")
        access = _RESOLVE_ACCESS_BY_LABEL.get(access_label, ResolveAccess.kRead)

        try:
            traits_data_out = resolve_entity(session, entity_reference, traits_data_in, access)
        except OpenAssetIOException as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        self.parameter_output_values["traits_data_out"] = traits_data_out
        self.parameter_output_values["session"] = session
        self.parameter_output_values["entity_reference"] = entity_reference

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Resolved {entity_reference}",
        )


# Maps the human-readable access dropdown to OpenAssetIO ResolveAccess values.
_RESOLVE_ACCESS_BY_LABEL: dict[str, ResolveAccess] = {
    "Read": ResolveAccess.kRead,
    "Manager Driven": ResolveAccess.kManagerDriven,
}
