# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Convert between file paths and file:// URLs using OpenAssetIO's FileUrlPathConverter.

Supports cross-platform conversion — a POSIX host can encode/decode Windows paths and
vice versa via the ``PathType`` parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

from openassetio.errors import InputValidationException
from openassetio.utils import FileUrlPathConverter, PathType


@dataclass(frozen=True)
class ConversionResult:
    """The output of a path/URL conversion.

    :param path: The filesystem path.
    :param file_url: The ``file://`` URL.
    """

    path: str
    file_url: str


class FileUrlPathBidirectionalConverter:
    """Convert between file paths and ``file://`` URLs.

    Composes an OpenAssetIO :class:`FileUrlPathConverter` instance and exposes a method
    to take either a file path or URL and return both.
    """

    _FILE_SCHEME = "file://"

    def __init__(self) -> None:
        """Create a new converter, compiling the internal regexes once."""
        self._converter = FileUrlPathConverter()

    def convert(self, input_value: str, path_type: PathType) -> ConversionResult:
        """Convert a file path to a URL or vice versa.

        Auto-detects the direction: if *input_value* starts with ``file://``
        (case-insensitive), it is decoded to a path; otherwise it is encoded to a
        ``file://`` URL. Both forms are always returned.

        :param input_value: A file path or ``file://`` URL.
        :param path_type: Platform interpretation for the path component.

        :returns: A :class:`ConversionResult` with both representations.

        :raises ValueError: If *input_value* is empty or the underlying converter
            rejects it.
        """
        stripped = input_value.strip()
        if not stripped:
            msg = "Input is empty"
            raise ValueError(msg)

        is_url = stripped.lower().startswith(self._FILE_SCHEME)

        try:
            path, url = (
                (self._converter.pathFromUrl(stripped, path_type), stripped)
                if is_url
                else (stripped, self._converter.pathToUrl(stripped, path_type))
            )
        except InputValidationException as exc:
            raise ValueError(str(exc)) from exc

        return ConversionResult(path=path, file_url=url)
