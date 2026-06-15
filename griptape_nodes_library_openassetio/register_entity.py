# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for registering OpenAssetIO entity references."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openassetio.access import PublishingAccess
    from openassetio.trait import TraitsData

    from griptape_nodes_library_openassetio.session import ManagerSession


def register_entity(
    session: ManagerSession,
    working_reference: str,
    traits_data: TraitsData,
    access: PublishingAccess,
) -> str:
    """Register an entity to finalise publication.

    Calls ``manager.register()`` with the working reference obtained from a prior
    ``preflight()`` call. Returns the final entity reference string that identifies the
    published data.

    :param session: An active OpenAssetIO session.
    :param working_reference: The working reference string from preflight.
    :param traits_data: ``TraitsData`` describing the published data.
    :param access: The publishing access mode (must match the preflight call).

    :returns: The final entity reference string.
    """
    working_ref = session.manager.createEntityReference(working_reference)
    final_ref = session.manager.register(working_ref, traits_data, access, session.context)
    return final_ref.toString()
