# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for unit tests."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from griptape_nodes_library_openassetio.session import ManagerSession
from openassetio import Context
from openassetio.hostApi import HostInterface, Manager


@pytest.fixture
def mock_session() -> ManagerSession:
    """Provide a single mock :class:`ManagerSession`.

    Returns a fresh session with independent mock ``Manager``, ``Context``, and
    ``HostInterface`` objects.

    :returns: A mock ``ManagerSession``.
    """
    return ManagerSession(
        manager=Mock(spec=Manager),
        context=Mock(spec=Context),
        host_interface=Mock(spec=HostInterface),
    )
