# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for preflighting OpenAssetIO entity references."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openassetio.access import PublishingAccess
    from openassetio.trait import TraitsData

    from griptape_nodes_library_openassetio.session import ManagerSession


def preflight_entity(
    session: ManagerSession,
    entity_reference: str,
    traits_data: TraitsData,
    access: PublishingAccess,
) -> str:
    """Preflight an entity reference for publishing.

    Calls ``manager.preflight()`` to signal intent to publish and obtain a working
    reference. The working reference may point to a staging location where the host
    should write data before calling ``manager.register()``.

    :param session: An active OpenAssetIO session.
    :param entity_reference: The target entity reference string.
    :param traits_data: ``TraitsData`` describing the data to be published.
    :param access: The publishing access mode (``kWrite`` or ``kCreateRelated``).

    :returns: The working reference string returned by the manager.
    """
    entity_ref = session.manager.createEntityReference(entity_reference)
    working_ref = session.manager.preflight(entity_ref, traits_data, access, session.context)
    return working_ref.toString()
