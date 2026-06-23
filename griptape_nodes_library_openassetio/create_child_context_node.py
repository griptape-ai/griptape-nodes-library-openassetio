# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""CreateChildContext node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import DataNode

from griptape_nodes_library_openassetio.create_child_context import create_child_context
from griptape_nodes_library_openassetio.session import ManagerSession


class CreateChildContext(DataNode):
    """Create an OpenAssetIO child context, optionally updating its locale.

    Creates a child context via ``manager.createChildContext()`` so that downstream
    nodes operate under an isolated context. If a ``locale`` ``TraitsData`` is
    connected, its traits and properties are merged into the child context's locale. The
    original session's context is not modified.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Create a child context, optionally updating its locale with trait data",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        # Session is mutated (child context created), so use separate
        # input and output parameters per the passthrough-vs-mutation rule.
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
                name="child_session",
                output_type="ManagerSession",
                tooltip="New session holding the child context",
                allowed_modes={ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="locale",
                input_types=["TraitsData"],
                tooltip=(
                    "Optional TraitsData to merge into the child context locale. "
                    "When not connected, the child locale is a copy of the parent's."
                ),
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )

    def validate_before_node_run(self) -> list[Exception] | None:
        """Check that the session input is present before execution.

        :returns: A list of validation errors, or ``None`` if all inputs are valid.
        """
        exceptions: list[Exception] = []
        session = self.get_parameter_value("session")
        if not isinstance(session, ManagerSession):
            exceptions.append(ValueError(f"{self.name}: No session connected"))
        return exceptions or None

    def process(self) -> None:
        """Create a child context and optionally merge locale into it."""
        session: ManagerSession = self.get_parameter_value("session")
        locale = self.get_parameter_value("locale")
        new_session = create_child_context(session, locale)
        self.parameter_output_values["child_session"] = new_session
