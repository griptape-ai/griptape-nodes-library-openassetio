# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""BAL fixtures for integration tests."""

from pathlib import Path

import pytest

_RESOURCES = Path(__file__).resolve().parent.parent / "resources"


@pytest.fixture
def bal_minimal_config() -> str:
    """Return the path to the minimal BAL config file."""
    return str(_RESOURCES / "openassetio.config.bal.minimal.toml")


@pytest.fixture
def openassetio_minimal_config_env(
    monkeypatch: pytest.MonkeyPatch,
    bal_minimal_config: str,
) -> str:
    """Set ``OPENASSETIO_DEFAULT_CONFIG`` to the BAL minimal config.

    :param monkeypatch: Pytest monkeypatch fixture.
    :param bal_minimal_config: Path to the minimal BAL config.

    :returns: The config file path that was set.
    """
    monkeypatch.setenv("OPENASSETIO_DEFAULT_CONFIG", bal_minimal_config)
    return bal_minimal_config
