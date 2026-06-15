# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""PreflightEntity node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes.traits.options import Options
from openassetio.access import PublishingAccess
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.preflight_entity import preflight_entity
from griptape_nodes_library_openassetio.session import ManagerSession


class PreflightEntity(SuccessFailureNode):
    """Preflight an entity reference for publishing.

    Calls ``manager.preflight()`` to signal intent to publish and obtain a working
    reference. The working reference may point to a staging location where the host
    should write data before calling ``manager.register()``.

    Session, traits_data, and publishing_access are passed through for downstream
    chaining to ``RegisterEntity``.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Preflight an entity reference for publishing",
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
                tooltip=(
                    "Target entity reference to publish to. Downstream nodes should then use the working_reference"
                    " parameter forsubsequent publishing operations (e.g. resolving target metadata, and final"
                    " registration)"
                ),
                # Unlike other nodes, we do not pass through the entity reference, since
                # downstream of preflight should use the working reference instead.
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="traits_data",
                input_types=["TraitsData"],
                output_type="TraitsData",
                tooltip=(
                    "TraitsData describing the data to publish. This should contain a complete trait set describing the"
                    " entity, along with populated properties if known ahead of time."
                ),
                allowed_modes={ParameterMode.INPUT, ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="publishing_access",
                type="str",
                default_value="Write",
                output_type="str",
                tooltip=(
                    "Publishing access mode. Use Write when publishing a new version of an existing entity. Use Create"
                    " Related when publishing a related but distinct entity (e.g. the target entity reference is a"
                    " container of some kind). If unsure, use Write."
                ),
                # Output the access mode so it can be reused by a downstream register.
                allowed_modes={ParameterMode.PROPERTY, ParameterMode.OUTPUT},
                traits={Options(choices=list(PUBLISHING_ACCESS_BY_LABEL.keys()))},
            )
        )
        self.add_parameter(
            Parameter(
                name="working_reference",
                output_type="str",
                tooltip=(
                    "Working reference returned by preflight. Should be used in all subsequent publishing operations "
                    " (e.g. resolving target metadata, and final registration)."
                ),
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the preflight operation result",
            result_details_placeholder="Preflight result will be shown here.",
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
        traits_data = self.get_parameter_value("traits_data")
        if traits_data is None:
            exceptions.append(ValueError(f"{self.name}: No traits data connected"))
        return exceptions or None

    def process(self) -> None:
        """Preflight the entity reference and output the working reference."""
        self._clear_execution_status()

        session: ManagerSession = self.get_parameter_value("session")
        entity_reference: str = self.get_parameter_value("entity_reference")
        traits_data = self.get_parameter_value("traits_data")
        access_label: str = self.get_parameter_value("publishing_access")
        # Safe to index directly — the dropdown constrains values to ACCESS_MAP keys.
        access = PUBLISHING_ACCESS_BY_LABEL[access_label]

        try:
            working_reference = preflight_entity(session, entity_reference, traits_data, access)
        except OpenAssetIOException as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        self.parameter_output_values["working_reference"] = working_reference
        self.parameter_output_values["session"] = session
        self.parameter_output_values["traits_data"] = traits_data
        self.parameter_output_values["publishing_access"] = access_label

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Preflighted {entity_reference}",
        )


# Maps the human-readable access dropdown to OpenAssetIO PublishingAccess values.
PUBLISHING_ACCESS_BY_LABEL: dict[str, PublishingAccess] = {
    "Write": PublishingAccess.kWrite,
    "Create Related": PublishingAccess.kCreateRelated,
}
