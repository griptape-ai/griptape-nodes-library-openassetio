# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the RelatedEntities node using BAL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from griptape_nodes_library_openassetio.related_entities_node import RelatedEntities
from griptape_nodes_library_openassetio.session_node import OpenAssetIOSession
from griptape_nodes_library_openassetio.trait_catalogue import load_default_catalogue
from openassetio.errors import BatchElementException
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes.exe_types.node_types import BaseNode
    from griptape_nodes.node_library.library_registry import NodeMetadata
    from griptape_nodes_library_openassetio.session import ManagerSession
    from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue


# Entity references for entities defined in
# openassetio.config.bal.relationship.toml.
_SHOT_REF = "bal:///test/shot"
_ISOLATED_REF = "bal:///test/isolated"


@pytest.fixture
def openassetio_bal_library(
    create_and_register_openassetio_library: Callable[
        [TraitCatalogue, tuple[tuple[type[BaseNode], NodeMetadata], ...]], str
    ],
) -> str:
    """Register a library with the real default catalogue for BAL tests."""
    return create_and_register_openassetio_library(load_default_catalogue(), ())


@pytest.mark.usefixtures("griptape_nodes", "openassetio_relationship_config_env")
class TestRelatedEntitiesNode:
    """Integration tests exercising RelatedEntities against BAL."""

    @pytest.fixture
    def session(self) -> ManagerSession:
        """Create a real BAL-backed session."""
        session_node = OpenAssetIOSession(name="session")
        session_node.process()
        return session_node.parameter_output_values["session"]

    @pytest.fixture
    def node(
        self,
        openassetio_bal_library: str,
        session: ManagerSession,
    ) -> RelatedEntities:
        """Create a RelatedEntities node wired to a real session."""
        node = RelatedEntities(
            name="test_gwr",
            metadata={"library": openassetio_bal_library},
        )
        node.parameter_values["session"] = session
        return node

    def test_queries_related_entities(self, node: RelatedEntities) -> None:
        """Querying relationships should return the expected entity references."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = _SHOT_REF
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        refs = node.parameter_output_values["related_references"]
        assert sorted(refs) == [
            "bal:///test/shot/asset_a",
            "bal:///test/shot/asset_b",
        ]

    def test_returns_empty_list_for_no_matching_relations(
        self,
        node: RelatedEntities,
    ) -> None:
        """An entity with no matching relations should return an empty list."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = _ISOLATED_REF
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        assert node.parameter_output_values["related_references"] == []

    def test_success_status_is_set(self, node: RelatedEntities) -> None:
        """Successful query sets the execution status."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = _SHOT_REF
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        assert node._execution_succeeded is True  # noqa: SLF001
        assert node.parameter_output_values["result_details"] == f"SUCCESS: Found 2 related entities for {_SHOT_REF}"

    def test_passes_through_session(
        self,
        node: RelatedEntities,
        session: ManagerSession,
    ) -> None:
        """Session should be passed through to the output."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = _SHOT_REF
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        assert node.parameter_output_values["session"] is session

    def test_passes_through_entity_reference(
        self,
        node: RelatedEntities,
    ) -> None:
        """Entity reference should be passed through to the output."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = _SHOT_REF
        node.parameter_values["relationship_traits_data"] = relationship_td

        node.process()

        assert node.parameter_output_values["entity_reference"] == _SHOT_REF

    def test_non_existent_entity_reports_failure(
        self,
        node: RelatedEntities,
    ) -> None:
        """Querying a non-existent entity sets failure status."""
        relationship_td = TraitsData({"openassetio-mediacreation:relationship.SourceRelationship"})
        node.parameter_values["entity_reference"] = "bal:///does/not/exist"
        node.parameter_values["relationship_traits_data"] = relationship_td

        with pytest.raises(BatchElementException, match="not found"):
            node.process()

        assert node._execution_succeeded is False  # noqa: SLF001
