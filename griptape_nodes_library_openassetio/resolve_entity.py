# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for resolving OpenAssetIO entity references."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openassetio.trait import TraitsData

if TYPE_CHECKING:
    from openassetio.access import ResolveAccess

    from griptape_nodes_library_openassetio.session import ManagerSession


def resolve_entity(
    session: ManagerSession,
    entity_reference: str,
    traits_data_in: TraitsData,
    access: ResolveAccess,
) -> TraitsData:
    """Resolve an entity reference and merge results into a copy of the input TraitsData.

    Calls ``manager.resolve()`` with the trait set from *traits_data_in*, then builds a
    new ``TraitsData`` from the input properties - treating them as defaults - and
    overwrites with any values the manager resolved.

    :param session: An active OpenAssetIO session.
    :param entity_reference: The entity reference string to resolve.
    :param traits_data_in: Input ``TraitsData`` whose trait set determines what to
        resolve. Not modified.
    :param access: The resolve access mode (``kRead`` or ``kManagerDriven``).

    :returns: A new ``TraitsData`` containing the input traits plus resolved property
        values. Where both the input and resolved data set the same property, the
        resolved value takes priority.
    """
    entity_ref = session.manager.createEntityReference(entity_reference)
    trait_set = traits_data_in.traitSet()

    # noinspection PyTypeChecker
    resolved: TraitsData = session.manager.resolve(entity_ref, trait_set, access, session.context)

    # Start from the input properties (defaults), then overwrite with resolved values.
    result = TraitsData(traits_data_in)
    _copy_properties(result, resolved)
    return result


def _copy_properties(target: TraitsData, source: TraitsData) -> None:
    """Copy all trait properties from source into target.

    Traits present in source but not in target are added.

    :param target: The ``TraitsData`` to copy into.
    :param source: The ``TraitsData`` to copy from.
    """
    for trait_id in source.traitSet():
        for key in source.traitPropertyKeys(trait_id):
            value = source.getTraitProperty(trait_id, key)
            # value is guaranteed non-None because key came from traitPropertyKeys.
            if value is not None:
                target.setTraitProperty(trait_id, key, value)
