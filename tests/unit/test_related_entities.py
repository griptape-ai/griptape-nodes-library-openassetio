# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for get_related_entities business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from griptape_nodes_library_openassetio.related_entities import (
    RelationshipCriteria,
    get_related_entities,
)
from openassetio import EntityReference
from openassetio.access import RelationsAccess
from openassetio.hostApi import EntityReferencePager
from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


class TestGetRelatedEntities:
    """Tests for the get_related_entities() function."""

    def test_returns_entity_reference_strings_from_pager(self, mock_session: ManagerSession) -> None:
        """get_related_entities should return strings from the pager's page."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager(["asset://child/1", "asset://child/2"])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td,
            result_traits_data=None,
            max_results=200,
        )
        result = get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        assert result == ["asset://child/1", "asset://child/2"]

    def test_returns_empty_list_for_empty_pager(self, mock_session: ManagerSession) -> None:
        """get_related_entities should return an empty list when pager has no results."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        criteria = RelationshipCriteria(
            relationship_traits_data=Mock(spec=TraitsData), result_traits_data=None, max_results=200
        )
        result = get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        assert result == []

    def test_creates_entity_reference_from_string(self, mock_session: ManagerSession) -> None:
        """get_related_entities should convert the string to an EntityReference."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        criteria = RelationshipCriteria(
            relationship_traits_data=Mock(spec=TraitsData), result_traits_data=None, max_results=200
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.createEntityReference.assert_called_once_with("asset://my/entity")

    def test_passes_relationship_traits_data_to_manager(self, mock_session: ManagerSession) -> None:
        """get_related_entities should pass the relationship TraitsData directly."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td,
            result_traits_data=None,
            max_results=200,
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj", relationship_td, 200, RelationsAccess.kRead, mock_session.context, set()
        )

    def test_extracts_trait_set_from_result_traits_data(self, mock_session: ManagerSession) -> None:
        """get_related_entities should extract the trait set from result_traits_data."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        result_td = Mock(spec=TraitsData)
        result_td.traitSet.return_value = {"test:content.LocatableContent"}

        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td,
            result_traits_data=result_td,
            max_results=200,
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj",
            relationship_td,
            200,
            RelationsAccess.kRead,
            mock_session.context,
            {"test:content.LocatableContent"},
        )

    def test_uses_empty_trait_set_when_result_traits_data_is_none(self, mock_session: ManagerSession) -> None:
        """get_related_entities should use an empty trait set when result_traits_data is None."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td, result_traits_data=None, max_results=200
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj", relationship_td, 200, RelationsAccess.kRead, mock_session.context, set()
        )

    def test_passes_max_results_as_page_size(self, mock_session: ManagerSession) -> None:
        """get_related_entities should pass max_results as the pageSize argument."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td, result_traits_data=None, max_results=50
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj", relationship_td, 50, RelationsAccess.kRead, mock_session.context, set()
        )

    def test_passes_access_mode_to_manager(self, mock_session: ManagerSession) -> None:
        """get_related_entities should use the provided access mode."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td, result_traits_data=None, max_results=200
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kCreateRelated)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj", relationship_td, 200, RelationsAccess.kCreateRelated, mock_session.context, set()
        )

    def test_passes_context_to_manager(self, mock_session: ManagerSession) -> None:
        """get_related_entities should pass the session context."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.return_value = _make_pager([])

        relationship_td = Mock(spec=TraitsData)
        criteria = RelationshipCriteria(
            relationship_traits_data=relationship_td, result_traits_data=None, max_results=200
        )
        get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)

        mock_manager.getWithRelationship.assert_called_once_with(
            "ref_obj", relationship_td, 200, RelationsAccess.kRead, mock_session.context, set()
        )

    def test_propagates_exception_from_manager(self, mock_session: ManagerSession) -> None:
        """Exceptions from manager.getWithRelationship() should propagate."""
        mock_manager = cast("Mock", mock_session.manager)
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.getWithRelationship.side_effect = RuntimeError("Relationship query failed")

        criteria = RelationshipCriteria(
            relationship_traits_data=Mock(spec=TraitsData), result_traits_data=None, max_results=200
        )
        with pytest.raises(RuntimeError, match="Relationship query failed"):
            get_related_entities(mock_session, "asset://my/entity", criteria, RelationsAccess.kRead)


def _make_pager(refs: list[str]) -> Mock:
    """Build a mock EntityReferencePager returning a single page of entity references.

    :param refs: Entity reference strings for the page.

    :returns: A mock pager whose ``get()`` returns mock ``EntityReference`` objects with
        ``.toString()`` returning the corresponding strings.
    """
    mock_refs = []
    for ref_str in refs:
        mock_ref = Mock(spec=EntityReference)
        mock_ref.toString.return_value = ref_str
        mock_refs.append(mock_ref)

    pager = Mock(spec=EntityReferencePager)
    pager.get.return_value = mock_refs
    return pager
