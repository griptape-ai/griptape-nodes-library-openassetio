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
from griptape_nodes_library_openassetio.trait_catalogue import (
    SpecificationDefinition,
    TraitCatalogue,
    TraitDefinition,
    TraitProperty,
)


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


@pytest.fixture
def stub_trait_catalogue() -> TraitCatalogue:
    """Build a small :class:`TraitCatalogue` for ResolveEntity tests.

    Contains four traits across three namespaces (content, identity, types), a v2
    variant of LocatableContent, and one specification. Shared by unit and integration
    tests that need a deterministic catalogue.

    :returns: A fresh :class:`TraitCatalogue` instance.
    """
    return TraitCatalogue(
        {
            "test:content.LocatableContent": TraitDefinition(
                trait_id="test:content.LocatableContent",
                package="test",
                namespace="content",
                member_name="LocatableContent",
                version="1",
                description="Locatable content trait",
                usage=["entity"],
                properties={
                    "location": TraitProperty(name="location", type="string", description="The location"),
                    "mimeType": TraitProperty(name="mimeType", type="string", description="The MIME type"),
                },
            ),
            "test:identity.DisplayName": TraitDefinition(
                trait_id="test:identity.DisplayName",
                package="test",
                namespace="identity",
                member_name="DisplayName",
                version="1",
                description="Display name trait",
                usage=["entity"],
                properties={
                    "name": TraitProperty(name="name", type="string", description="The name"),
                },
            ),
            "test:types.Mixed": TraitDefinition(
                trait_id="test:types.Mixed",
                package="test",
                namespace="types",
                member_name="Mixed",
                version="1",
                description="Trait with mixed property types",
                usage=["entity"],
                properties={
                    "count": TraitProperty(name="count", type="integer", description="An int"),
                    "ratio": TraitProperty(name="ratio", type="float", description="A float"),
                    "enabled": TraitProperty(name="enabled", type="boolean", description="A bool"),
                },
            ),
            "test:content.LocatableContent.v2": TraitDefinition(
                trait_id="test:content.LocatableContent.v2",
                package="test",
                namespace="content",
                member_name="LocatableContent",
                version="2",
                description="Locatable content trait v2",
                usage=["entity"],
                properties={
                    "location": TraitProperty(name="location", type="string", description="The location"),
                },
            ),
        },
        specifications={
            "test:specification:content.NamedContent": SpecificationDefinition(
                spec_id="test:specification:content.NamedContent",
                package="test",
                namespace="content",
                member_name="NamedContent",
                description="Content with a display name",
                usage=["entity"],
                trait_ids=[
                    "test:content.LocatableContent",
                    "test:identity.DisplayName",
                ],
            ),
        },
        package_descriptions={"test": "Test package description"},
        namespace_descriptions={
            "test:content": "Content namespace description",
            "test:identity": "Identity namespace description",
            "test:types": "Types namespace description",
        },
    )
