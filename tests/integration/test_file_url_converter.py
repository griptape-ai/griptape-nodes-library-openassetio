# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for file_url_converter exercising the real C++ binding."""

from __future__ import annotations

import pytest
from griptape_nodes_library_openassetio.file_url_converter import FileUrlPathBidirectionalConverter
from openassetio.utils import PathType


class TestConvertRoundTrip:
    """Round-trip tests using the real FileUrlPathConverter binding."""

    @pytest.fixture
    def converter(self) -> FileUrlPathBidirectionalConverter:
        """Create a FileUrlPathCompleter with the real C++ binding."""
        return FileUrlPathBidirectionalConverter()

    def test_posix_path_round_trips(self, converter: FileUrlPathBidirectionalConverter) -> None:
        """A POSIX path should round-trip through URL and back."""
        path = "/home/user/textures/brick.exr"

        to_url = converter.convert(path, PathType.kPOSIX)
        from_url = converter.convert(to_url.file_url, PathType.kPOSIX)

        assert to_url.path == path
        assert to_url.file_url == "file:///home/user/textures/brick.exr"
        assert from_url.path == path
        assert from_url.file_url == to_url.file_url

    def test_windows_path_round_trips(self, converter: FileUrlPathBidirectionalConverter) -> None:
        """A Windows path should round-trip through URL and back."""
        path = "C:\\Users\\artist\\textures\\brick.exr"

        to_url = converter.convert(path, PathType.kWindows)
        from_url = converter.convert(to_url.file_url, PathType.kWindows)

        assert from_url.path == path
        assert from_url.file_url == to_url.file_url

    def test_relative_path_raises(self, converter: FileUrlPathBidirectionalConverter) -> None:
        """The real binding should reject a relative path."""
        with pytest.raises(ValueError, match=r"[Rr]elative"):
            converter.convert("relative/path.txt", PathType.kPOSIX)

    def test_path_with_spaces(self, converter: FileUrlPathBidirectionalConverter) -> None:
        """Paths with spaces should be percent-encoded in the URL."""
        path = "/home/user/my project/file.txt"

        result = converter.convert(path, PathType.kPOSIX)

        # Spaces are percent-encoded in file:// URLs.
        assert "%20" in result.file_url
        # Round-trip should recover the original path.
        back = converter.convert(result.file_url, PathType.kPOSIX)
        assert back.path == path
