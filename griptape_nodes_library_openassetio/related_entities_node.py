# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""RelatedEntities node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes.traits.options import Options
from openassetio.access import RelationsAccess
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.related_entities import (
    RelationshipCriteria,
    get_related_entities,
)
from griptape_nodes_library_openassetio.session import ManagerSession


class RelatedEntities(SuccessFailureNode):
    """Query related entities via the asset manager's relationship API.

    Takes a source entity reference and a ``TraitsData`` describing the relationship
    type to query. Optionally accepts a second ``TraitsData`` whose trait set constrains
    the type of returned entities. Calls ``manager.getWithRelationship()`` and outputs a
    list of related entity reference strings.

    Session and entity_reference are passed through for downstream chaining.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Query related entities via the asset manager's relationship API",
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
                tooltip="Source entity reference to query relationships for",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="relationship_traits_data",
                input_types=["TraitsData"],
                tooltip="TraitsData describing the relationship type to query",
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="result_traits_data",
                input_types=["TraitsData"],
                tooltip="Optional TraitsData constraining the type of returned entities",
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
                    "Relations access mode. Use Read for querying a list of entities that already exist. Use Write when"
                    " decomposing a working reference from a PreflightEntity node into multiple pre-existing"
                    " components. Use Create Related when decomposing a working reference from PreflightEntity into"
                    " multiple new components."
                ),
                allowed_modes={ParameterMode.PROPERTY},
                traits={Options(choices=list(_RELATIONSHIP_ACCESS_BY_LABEL.keys()))},
            )
        )
        self.add_parameter(
            Parameter(
                name="max_results",
                type="int",
                default_value=200,
                tooltip="Maximum number of related entities to return (passed as page size to the manager)",
                allowed_modes={ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="related_references",
                output_type="list",
                tooltip="List of related entity reference strings",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the relationship query result",
            result_details_placeholder="Relationship query result will be shown here.",
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
        relationship_traits_data = self.get_parameter_value("relationship_traits_data")
        if relationship_traits_data is None:
            exceptions.append(ValueError(f"{self.name}: No relationship traits data connected"))
        return exceptions or None

    def process(self) -> None:
        """Query related entities and output the reference strings."""
        self._clear_execution_status()

        session: ManagerSession = self.get_parameter_value("session")
        entity_reference: str = self.get_parameter_value("entity_reference")
        relationship_traits_data = self.get_parameter_value("relationship_traits_data")
        result_traits_data = self.get_parameter_value("result_traits_data")
        access_label: str = self.get_parameter_value("access")
        access = _RELATIONSHIP_ACCESS_BY_LABEL.get(access_label, RelationsAccess.kRead)
        max_results: int = self.get_parameter_value("max_results")

        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_traits_data,
            result_traits_data=result_traits_data,
            max_results=max_results,
        )

        try:
            related_refs = get_related_entities(session, entity_reference, criteria, access)
        except OpenAssetIOException as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        self.parameter_output_values["related_references"] = related_refs
        self.parameter_output_values["session"] = session
        self.parameter_output_values["entity_reference"] = entity_reference

        count = len(related_refs)
        noun = "entity" if count == 1 else "entities"
        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Found {count} related {noun} for {entity_reference}",
        )


# Maps the human-readable access dropdown to OpenAssetIO RelationsAccess values.
_RELATIONSHIP_ACCESS_BY_LABEL: dict[str, RelationsAccess] = {
    "Read": RelationsAccess.kRead,
    "Write": RelationsAccess.kWrite,
    "Create Related": RelationsAccess.kCreateRelated,
}
