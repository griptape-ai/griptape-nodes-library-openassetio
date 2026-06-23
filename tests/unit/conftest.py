# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest
from griptape_nodes_library_openassetio.session import ManagerSession
from openassetio import Context
from openassetio.hostApi import HostInterface, Manager


@pytest.fixture
def make_mock_session() -> Callable[[], ManagerSession]:
    """Provide a factory for creating mock :class:`ManagerSession` instances.

    Each call returns a fresh session with independent mock ``Manager``, ``Context``,
    and ``HostInterface`` objects. Use in tests that need one or more sessions without
    coupling to the concrete OpenAssetIO bootstrap.

    :returns: A callable that creates a new mock ``ManagerSession`` on each invocation.
    """

    def _factory() -> ManagerSession:
        return ManagerSession(
            manager=Mock(spec=Manager),
            context=Mock(spec=Context),
            host_interface=Mock(spec=HostInterface),
        )

    return _factory


@pytest.fixture
def mock_session(make_mock_session: Callable[[], ManagerSession]) -> ManagerSession:
    """Provide a single mock :class:`ManagerSession`.

    Convenience wrapper around :func:`make_mock_session` for the common case where a
    test only needs one session. Tests that need multiple independent sessions should
    use ``make_mock_session`` directly.

    :returns: A fresh mock ``ManagerSession``.
    """
    return make_mock_session()
