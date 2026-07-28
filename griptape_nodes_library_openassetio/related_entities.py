# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for querying related OpenAssetIO entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openassetio.access import RelationsAccess
    from openassetio.trait import TraitsData

    from griptape_nodes_library_openassetio.session import ManagerSession


@dataclass(frozen=True)
class RelationshipCriteria:
    """Criteria for a relationship query.

    :param relationship_traits_data: ``TraitsData`` describing the relationship type and
        optional filter properties.
    :param result_traits_data: Optional ``TraitsData`` whose trait set constrains the
        type of returned entities. ``None`` means no constraint (empty trait set).
    :param max_results: Maximum number of related entities to return. Passed as the
        ``pageSize`` argument to the manager — only the first page is consumed.
    """

    relationship_traits_data: TraitsData
    result_traits_data: TraitsData | None
    max_results: int


def get_related_entities(
    session: ManagerSession,
    entity_reference: str,
    criteria: RelationshipCriteria,
    access: RelationsAccess,
) -> list[str]:
    """Query an asset manager for entities related to a source entity.

    Calls ``manager.getWithRelationship()`` with the supplied relationship criteria and
    returns up to ``criteria.max_results`` related entity reference strings.

    Only the first page is consumed. ``max_results`` is passed directly as the pager's
    ``pageSize``, so the manager returns at most that many entities in a single page.
    Griptape Nodes does not support paginated outputs, so draining additional pages is
    intentionally omitted.

    :param session: An active OpenAssetIO session.
    :param entity_reference: The source entity reference string.
    :param criteria: Relationship query criteria.
    :param access: The relations access mode.

    :returns: A list of related entity reference strings (at most ``max_results``).
    """
    entity_ref = session.manager.createEntityReference(entity_reference)
    result_trait_set = criteria.result_traits_data.traitSet() if criteria.result_traits_data else set()

    # noinspection PyTypeChecker
    pager = session.manager.getWithRelationship(
        entity_ref,
        criteria.relationship_traits_data,
        criteria.max_results,
        access,
        session.context,
        result_trait_set,
    )

    # Only consume the first page — max_results controls the page size, so
    # all requested results arrive in a single get().
    return [ref.toString() for ref in pager.get()]
