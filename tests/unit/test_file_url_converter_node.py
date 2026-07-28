# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the FileUrlConverter node."""

from __future__ import annotations

from unittest.mock import Mock, create_autospec

import griptape_nodes_library_openassetio.file_url_converter as logic_mod
import pytest
from griptape_nodes.exe_types.core_types import ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes_library_openassetio.file_url_converter import ConversionResult
from griptape_nodes_library_openassetio.file_url_converter_node import (
    FileUrlConverter,
)
from openassetio.utils import PathType


@pytest.mark.usefixtures("griptape_nodes")
class TestFileUrlConverterStructure:
    """Tests for parameter setup and node metadata."""

    @pytest.fixture
    def node(self) -> FileUrlConverter:
        return FileUrlConverter(name="test_converter")

    def test_is_success_failure_node(self, node: FileUrlConverter) -> None:
        assert isinstance(node, SuccessFailureNode)

    def test_default_metadata(self, node: FileUrlConverter) -> None:
        assert node.metadata["category"] == "OpenAssetIO"

    def test_custom_metadata_merges_with_defaults(self) -> None:
        node = FileUrlConverter(name="test_custom", metadata={"custom_key": "val"})
        assert node.metadata["category"] == "OpenAssetIO"
        assert node.metadata["custom_key"] == "val"

    # -- path_or_url parameter --

    def test_has_path_or_url_parameter(self, node: FileUrlConverter) -> None:
        param = node.get_parameter_by_name("path_or_url")
        assert param is not None
        assert param.type == "str"
        assert param.output_type == "str"
        assert param.allowed_modes == {
            ParameterMode.INPUT,
            ParameterMode.PROPERTY,
            ParameterMode.OUTPUT,
        }

    # -- path_type parameter --

    def test_has_path_type_parameter(self, node: FileUrlConverter) -> None:
        param = node.get_parameter_by_name("path_type")
        assert param is not None
        assert param.type == "str"
        assert param.allowed_modes == {ParameterMode.INPUT, ParameterMode.PROPERTY}

    def test_path_type_default_is_system(self, node: FileUrlConverter) -> None:
        param = node.get_parameter_by_name("path_type")
        assert param is not None
        assert param.default_value == "System"

    # -- output parameters --

    def test_has_path_output(self, node: FileUrlConverter) -> None:
        param = node.get_parameter_by_name("path")
        assert param is not None
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    def test_has_file_url_output(self, node: FileUrlConverter) -> None:
        param = node.get_parameter_by_name("file_url")
        assert param is not None
        assert param.output_type == "str"
        assert param.allowed_modes == {ParameterMode.OUTPUT}

    # -- Converter composition --

    def test_has_converter_instance(self, node: FileUrlConverter) -> None:
        """The node should compose a FileUrlConverter logic instance."""
        assert isinstance(node._converter, logic_mod.FileUrlPathBidirectionalConverter)  # noqa: SLF001


@pytest.mark.usefixtures("griptape_nodes")
class TestFileUrlConverterValidation:
    """Tests for FileUrlConverter validate_before_node_run."""

    @pytest.fixture
    def node(self) -> FileUrlConverter:
        return FileUrlConverter(name="test_converter_val")

    def test_validate_returns_none_when_input_present(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should pass when input is provided."""
        node.parameter_values["path_or_url"] = "/some/path"
        node.parameter_values["path_type"] = "System"

        assert node.validate_before_node_run() is None

    def test_validate_returns_error_when_input_missing(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should fail when input is empty."""
        node.parameter_values["path_type"] = "System"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No input provided" in str(errors[0])

    def test_validate_returns_error_when_input_whitespace_only(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should fail when input is whitespace-only."""
        node.parameter_values["path_or_url"] = "   "
        node.parameter_values["path_type"] = "System"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "No input provided" in str(errors[0])

    def test_validate_returns_error_when_path_type_unknown(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should fail when path_type is not in the map."""
        node.parameter_values["path_or_url"] = "/some/path"
        node.parameter_values["path_type"] = "BadValue"

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "Unknown path_type 'BadValue'" in str(errors[0])
        assert "POSIX" in str(errors[0])

    def test_validate_returns_error_when_path_type_none(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should fail when path_type is None."""
        node.parameter_values["path_or_url"] = "/some/path"
        node.parameter_values["path_type"] = None

        errors = node.validate_before_node_run()

        assert errors is not None
        assert len(errors) == 1
        assert "Unknown path_type" in str(errors[0])

    def test_validate_passes_with_valid_path_type(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should pass when path_type is valid."""
        node.parameter_values["path_or_url"] = "/some/path"
        node.parameter_values["path_type"] = "POSIX"

        assert node.validate_before_node_run() is None

    def test_validate_passes_with_default_path_type(self, node: FileUrlConverter) -> None:
        """validate_before_node_run should use the default path_type when not explicitly set."""
        node.parameter_values["path_or_url"] = "/some/path"
        # Do NOT set path_type — it should fall back to the default "System".

        assert node.validate_before_node_run() is None


@pytest.mark.usefixtures("griptape_nodes")
class TestFileUrlConverterProcess:
    """Tests for the process() method."""

    @pytest.fixture
    def node(self) -> FileUrlConverter:
        return FileUrlConverter(name="test_converter")

    # -- Success paths --

    def test_process_sets_outputs_from_convert(self, node: FileUrlConverter, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_logic = Mock(spec=logic_mod.FileUrlPathBidirectionalConverter)
        mock_logic.convert.return_value = ConversionResult(
            path="/home/user/file.txt", file_url="file:///home/user/file.txt"
        )
        monkeypatch.setattr(node, "_converter", mock_logic)

        node.parameter_values["path_or_url"] = "/home/user/file.txt"
        node.parameter_values["path_type"] = "System"

        node.process()

        assert node.parameter_output_values["path"] == "/home/user/file.txt"
        assert node.parameter_output_values["file_url"] == "file:///home/user/file.txt"
        assert node.parameter_output_values["path_or_url"] == "/home/user/file.txt"
        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Converted '/home/user/file.txt'"

    def test_process_forwards_posix_path_type(self, node: FileUrlConverter, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_logic = Mock(spec=logic_mod.FileUrlPathBidirectionalConverter)
        mock_logic.convert.return_value = ConversionResult(path="/p", file_url="file:///p")
        monkeypatch.setattr(node, "_converter", mock_logic)

        node.parameter_values["path_or_url"] = "/p"
        node.parameter_values["path_type"] = "POSIX"

        node.process()

        mock_logic.convert.assert_called_once_with("/p", PathType.kPOSIX)
        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Converted '/p'"

    def test_process_forwards_windows_path_type(self, node: FileUrlConverter, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_logic = Mock(spec=logic_mod.FileUrlPathBidirectionalConverter)
        mock_logic.convert.return_value = ConversionResult(path="C:\\file.txt", file_url="file:///C:/file.txt")
        monkeypatch.setattr(node, "_converter", mock_logic)

        node.parameter_values["path_or_url"] = "C:\\file.txt"
        node.parameter_values["path_type"] = "Windows"

        node.process()

        mock_logic.convert.assert_called_once_with("C:\\file.txt", PathType.kWindows)
        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "SUCCESS: Converted 'C:\\file.txt'"

    # -- Failure paths --

    def test_process_fails_when_convert_raises(self, node: FileUrlConverter, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_logic = Mock(spec=logic_mod.FileUrlPathBidirectionalConverter)
        mock_logic.convert.side_effect = ValueError("Path is relative ('rel')")
        monkeypatch.setattr(node, "_converter", mock_logic)

        mock_handle = create_autospec(node._handle_failure_exception)  # noqa: SLF001
        monkeypatch.setattr(node, "_handle_failure_exception", mock_handle)

        node.parameter_values["path_or_url"] = "rel"
        node.parameter_values["path_type"] = "System"

        node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == "FAILURE: Path is relative ('rel')"
        mock_handle.assert_called_once()
        # Verify the exception passed to _handle_failure_exception is the ValueError.
        exc_arg = mock_handle.call_args[0][0]
        assert isinstance(exc_arg, ValueError)
        assert str(exc_arg) == "Path is relative ('rel')"
