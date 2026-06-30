# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the file_url_converter logic module."""

from __future__ import annotations

from unittest.mock import Mock

import griptape_nodes_library_openassetio.file_url_converter as mod
import pytest
from griptape_nodes_library_openassetio.file_url_converter import ConversionResult
from openassetio.errors import InputValidationException
from openassetio.utils import FileUrlPathConverter as OaioConverter
from openassetio.utils import PathType


class TestFileUrlPathCompleterInit:
    """Tests for FileUrlPathCompleter construction."""

    def test_constructor_creates_converter(self) -> None:
        """The constructor should create a FileUrlPathConverter instance."""
        converter = mod.FileUrlPathBidirectionalConverter()

        # Verify the composed converter is a real FileUrlPathConverter.
        assert isinstance(converter._converter, OaioConverter)  # noqa: SLF001


class TestConvert:
    """Tests for the FileUrlPathCompleter.convert() method."""

    @pytest.fixture
    def converter(self) -> mod.FileUrlPathBidirectionalConverter:
        """Create a FileUrlPathCompleter instance for each test."""
        return mod.FileUrlPathBidirectionalConverter()

    # -- Auto-detection --

    def test_path_input_returns_both_outputs(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A plain path input should produce both path and file_url outputs."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathToUrl.return_value = "file:///home/user/file.txt"
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        result = converter.convert("/home/user/file.txt", PathType.kSystem)

        assert result.path == "/home/user/file.txt"
        assert result.file_url == "file:///home/user/file.txt"
        mock_oaio.pathToUrl.assert_called_once_with("/home/user/file.txt", PathType.kSystem)

    def test_url_input_returns_both_outputs(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A file:// URL input should produce both path and file_url outputs."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathFromUrl.return_value = "/home/user/file.txt"
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        result = converter.convert("file:///home/user/file.txt", PathType.kSystem)

        assert result.path == "/home/user/file.txt"
        assert result.file_url == "file:///home/user/file.txt"
        mock_oaio.pathFromUrl.assert_called_once_with("file:///home/user/file.txt", PathType.kSystem)

    def test_url_detection_is_case_insensitive(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """file:// detection should be case-insensitive per RFC 3986."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathFromUrl.return_value = "/some/path"
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        converter.convert("FILE:///some/path", PathType.kSystem)

        mock_oaio.pathFromUrl.assert_called_once_with("FILE:///some/path", PathType.kSystem)

    # -- PathType forwarding --

    def test_posix_path_type_forwarded(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PathType.kPOSIX should be forwarded to the converter."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathToUrl.return_value = "file:///posix/path"
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        converter.convert("/posix/path", PathType.kPOSIX)

        mock_oaio.pathToUrl.assert_called_once_with("/posix/path", PathType.kPOSIX)

    def test_windows_path_type_forwarded(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PathType.kWindows should be forwarded to the converter."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathToUrl.return_value = "file:///C:/Users/file.txt"
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        converter.convert("C:\\Users\\file.txt", PathType.kWindows)

        mock_oaio.pathToUrl.assert_called_once_with("C:\\Users\\file.txt", PathType.kWindows)

    # -- Error handling --

    def test_empty_input_raises_value_error(self, converter: mod.FileUrlPathBidirectionalConverter) -> None:
        """An empty string should raise ValueError."""
        with pytest.raises(ValueError, match="Input is empty"):
            converter.convert("", PathType.kSystem)

    def test_whitespace_only_input_raises_value_error(self, converter: mod.FileUrlPathBidirectionalConverter) -> None:
        """A whitespace-only string should raise ValueError."""
        with pytest.raises(ValueError, match="Input is empty"):
            converter.convert("   ", PathType.kSystem)

    def test_converter_error_wrapped_as_value_error(
        self, converter: mod.FileUrlPathBidirectionalConverter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """InputValidationException from the converter should be wrapped in ValueError."""
        mock_oaio = Mock(spec=OaioConverter)
        mock_oaio.pathToUrl.side_effect = InputValidationException("Path is relative ('rel')")
        monkeypatch.setattr(converter, "_converter", mock_oaio)

        with pytest.raises(ValueError, match="Path is relative"):
            converter.convert("rel", PathType.kSystem)


class TestMacroInputBehaviour:
    """Confidence checks for how unresolved Griptape macros fare through conversion.

    These exercise the real OpenAssetIO ``FileUrlPathConverter`` (no mocking) to
    document the behaviour. Macro resolution is intentionally out of scope for this
    converter (see the ``path_or_url`` tooltip on the node): macros are passed through
    verbatim, and users should resolve them upstream (e.g. a ResolveMacroPath node)
    before conversion.
    """

    @pytest.fixture
    def converter(self) -> mod.FileUrlPathBidirectionalConverter:
        """Create a converter backed by the real OpenAssetIO utility (no mocks)."""
        return mod.FileUrlPathBidirectionalConverter()

    # -- Encode direction (path -> URL) --

    def test_absolute_macro_path_encodes_braces_verbatim(
        self, converter: mod.FileUrlPathBidirectionalConverter
    ) -> None:
        """An absolute path with macro braces is encoded verbatim, not resolved."""
        result = converter.convert("/{outputs}/image.png", PathType.kPOSIX)

        assert result.path == "/{outputs}/image.png"
        assert result.file_url == "file:///%7Boutputs%7D/image.png"

    def test_absolute_windows_macro_path_encodes_braces_verbatim(
        self, converter: mod.FileUrlPathBidirectionalConverter
    ) -> None:
        """A Windows macro path is encoded cross-platform with braces retained verbatim."""
        result = converter.convert("C:\\{outputs}\\image.png", PathType.kWindows)

        assert result.path == "C:\\{outputs}\\image.png"
        assert result.file_url == "file:///C:/%7Boutputs%7D/image.png"

    def test_relative_macro_path_fails(self, converter: mod.FileUrlPathBidirectionalConverter) -> None:
        """A relative macro path fails the no-relative-path constraint.

        Because macros are not resolved, a leading macro leaves the path relative, which
        ``pathToUrl`` rejects.
        """
        with pytest.raises(ValueError, match="Path is relative"):
            converter.convert("{workflow_dir?:/}outputs", PathType.kPOSIX)

    # -- Decode direction (URL -> path) --

    def test_url_with_encoded_macro_decodes_to_literal_braces(
        self, converter: mod.FileUrlPathBidirectionalConverter
    ) -> None:
        """A file:// URL with percent-encoded macro braces decodes to the literal macro path.

        The recovered ``/{outputs}/image.png`` is ready for downstream macro resolution.
        """
        result = converter.convert("file:///%7Boutputs%7D/image.png", PathType.kPOSIX)

        assert result.path == "/{outputs}/image.png"
        assert result.file_url == "file:///%7Boutputs%7D/image.png"

    def test_url_with_macro_containing_separator_fails(self, converter: mod.FileUrlPathBidirectionalConverter) -> None:
        """A macro whose format embeds a path separator cannot survive a URL round-trip.

        The ``/`` inside ``{workflow_dir?:/}`` encodes to ``%2F``, which OpenAssetIO
        rejects as a percent-encoded path separator.
        """
        with pytest.raises(ValueError, match="Percent-encoded path separator"):
            converter.convert("file:///%7Bworkflow_dir%3F%3A%2F%7Doutputs/", PathType.kPOSIX)


class TestConversionResult:
    """Tests for the ConversionResult dataclass."""

    def test_fields_are_accessible(self) -> None:
        """ConversionResult should expose path and file_url fields."""
        result = ConversionResult(path="/a/b", file_url="file:///a/b")

        assert result.path == "/a/b"
        assert result.file_url == "file:///a/b"
