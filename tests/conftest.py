# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures and setup for all tests."""

import json
from pathlib import Path

import pytest
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes
from griptape_nodes.retained_mode.managers import config_manager
from griptape_nodes.utils.metaclasses import SingletonMeta


@pytest.fixture(autouse=True)
def isolate_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate the user config file during tests."""
    # GriptapeNodes and its managers (ConfigManager, SyncManager, etc.) are
    # singletons via SingletonMeta.  Clear them so each test gets a fresh
    # instance that reads our temporary config instead of stale state from
    # a previous test.
    SingletonMeta._instances.clear()  # noqa: SLF001 — no public API to reset singletons

    # Write a minimal config that redirects the workspace directory
    # into the temp dir, preventing SyncManager from creating a
    # GriptapeNodes/synced_workflows/ directory inside the repo.
    temp_config_path = tmp_path / "griptape_nodes_config.json"
    workspace_dir = str(tmp_path / "GriptapeNodes")
    temp_config_path.write_text(json.dumps({"workspace_directory": workspace_dir}, indent=2))

    # Patch the module-level USER_CONFIG_PATH so ConfigManager loads
    # our temp config instead of the real user config on disk.
    monkeypatch.setattr(config_manager, "USER_CONFIG_PATH", temp_config_path)

    return temp_config_path


@pytest.fixture
def griptape_nodes() -> GriptapeNodes:
    """Provide a properly initialized GriptapeNodes instance for testing."""
    return GriptapeNodes()
