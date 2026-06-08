# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for resolving OpenAssetIO entity references."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openassetio.access import ResolveAccess

if TYPE_CHECKING:
    from griptape_nodes_library_openassetio.session import ManagerSession


def resolve_entity(
    session: ManagerSession,
    entity_reference: str,
    trait_ids: set[str],
) -> dict[str, str | int | float | bool]:
    """Resolve an entity reference and return its trait property values.

    Calls ``manager.resolve()`` with the given trait IDs and flattens the resulting
    :class:`~openassetio.trait.TraitsData` into a dict keyed by
    ``{trait_id}.{property_key}``.

    :param session: An active OpenAssetIO session.
    :param entity_reference: The entity reference string to resolve.
    :param trait_ids: Set of trait IDs to request from the manager.

    :returns: Mapping of ``{trait_id}.{property_key}`` to resolved value.
    """
    entity_ref = session.manager.createEntityReference(entity_reference)
    traits_data = session.manager.resolve(entity_ref, trait_ids, ResolveAccess.kRead, session.context)

    results: dict[str, str | int | float | bool] = {}
    for resolved_trait_id in traits_data.traitSet():
        for prop_key in traits_data.traitPropertyKeys(resolved_trait_id):
            value = traits_data.getTraitProperty(resolved_trait_id, prop_key)
            # traitPropertyKeys only reports keys with set values.
            results[f"{resolved_trait_id}.{prop_key}"] = value  # pyright: ignore[reportArgumentType]

    return results
