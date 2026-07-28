# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""FileUrlConverter node for Griptape Nodes."""

from __future__ import annotations

from typing import Any

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes.traits.options import Options
from openassetio.utils import PathType

from griptape_nodes_library_openassetio import file_url_converter

# Maps dropdown labels to OpenAssetIO PathType values.
_PATH_TYPE_MAP: dict[str, PathType] = {
    "System": PathType.kSystem,
    "POSIX": PathType.kPOSIX,
    "Windows": PathType.kWindows,
}


class FileUrlConverter(SuccessFailureNode):
    """Convert between file paths and ``file://`` URLs.

    Accepts either a filesystem path or a ``file://`` URL as input and outputs both
    representations. The *path_type* dropdown selects the platform interpretation -
    enabling cross-platform conversion (e.g. encoding a Windows path on a Linux host).
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata: dict[str, Any] = {
            "category": "OpenAssetIO",
            "description": "Convert between file paths and file:// URLs with cross-platform support",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        # Construct in init since construction isn't cheap (compiles regexes). Is fast
        # and idempotent to use once constructed.
        self._converter = file_url_converter.FileUrlPathBidirectionalConverter()

        self.add_parameter(
            Parameter(
                name="path_or_url",
                type="str",
                output_type="str",
                default_value="",
                tooltip=(
                    "A file path or file:// URL to convert. Macro paths (e.g. '{workflow_dir?:/}outputs') are NOT"
                    " resolved and will be retained verbatim (very likely failing conversion)."
                ),
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY, ParameterMode.OUTPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="path_type",
                type="str",
                default_value="System",
                tooltip="Platform interpretation for the path component",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                traits={Options(choices=list(_PATH_TYPE_MAP.keys()))},
            )
        )
        self.add_parameter(
            Parameter(
                name="path",
                output_type="str",
                tooltip="The filesystem path",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )
        self.add_parameter(
            Parameter(
                name="file_url",
                output_type="str",
                tooltip="The file:// URL",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the conversion result",
            result_details_placeholder="Conversion status will be shown here.",
        )

    def validate_before_node_run(self) -> list[Exception] | None:
        """Check that the input is present before execution.

        :returns: A list of validation errors, or ``None`` if all inputs are valid.
        """
        exceptions: list[Exception] = []
        input_value = self.get_parameter_value("path_or_url")
        if not input_value or not input_value.strip():
            exceptions.append(ValueError(f"{self.name}: No input provided"))
        # path_type is an INPUT parameter, so an incoming connection could supply an
        # unexpected value that bypasses the Options dropdown.
        path_type_label = self.get_parameter_value("path_type")
        if path_type_label not in _PATH_TYPE_MAP:
            valid = ", ".join(sorted(_PATH_TYPE_MAP))
            exceptions.append(
                ValueError(f"{self.name}: Unknown path_type '{path_type_label}'. Expected one of: {valid}")
            )
        return exceptions or None

    def process(self) -> None:
        """Convert the input and populate outputs."""
        self._clear_execution_status()

        # The engine guarantees these keys exist (both have default_value set).
        input_value: str = self.get_parameter_value("path_or_url")
        path_type_label: str = self.get_parameter_value("path_type")
        path_type = _PATH_TYPE_MAP[path_type_label]

        try:
            result = self._converter.convert(input_value, path_type)
        except ValueError as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        self.parameter_output_values["path_or_url"] = input_value
        self.parameter_output_values["path"] = result.path
        self.parameter_output_values["file_url"] = result.file_url

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Converted '{input_value}'",
        )
