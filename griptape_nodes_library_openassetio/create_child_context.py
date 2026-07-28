# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Business logic for creating an OpenAssetIO child context."""

from __future__ import annotations

from typing import TYPE_CHECKING

from griptape_nodes_library_openassetio.session import ManagerSession

if TYPE_CHECKING:
    from openassetio.trait import TraitsData


def create_child_context(
    session: ManagerSession,
    locale: TraitsData | None = None,
) -> ManagerSession:
    """Create a child context, optionally merging locale traits into it.

    Calls ``manager.createChildContext()`` to produce a new ``Context`` with a
    deep-copied locale and duplicated manager state. If *locale* is provided, its
    properties are merged into the child context's locale, preserving any traits already
    present from the parent.

    :param session: An active OpenAssetIO session.
    :param locale: Optional ``TraitsData`` containing traits and properties to merge
        into the child context's locale. When ``None``, the child context's locale is
        left as a copy of the parent's.

    :returns: A new :class:`ManagerSession` sharing the same manager and host interface
        but holding the child context.
    """
    child_context = session.manager.createChildContext(session.context)
    if locale is not None:
        _merge_traits_data(child_context.locale, locale)
    return ManagerSession(
        manager=session.manager,
        context=child_context,
        host_interface=session.host_interface,
    )


def _merge_traits_data(target: TraitsData, source: TraitsData) -> None:
    """Merge all traits and properties from *source* into *target*.

    Traits already present in *target* are preserved; properties from *source* overwrite
    properties with the same key.

    :param target: The ``TraitsData`` to merge into (mutated in place).
    :param source: The ``TraitsData`` to read traits and properties from.
    """
    source_traits = source.traitSet()
    target.addTraits(source_traits)
    for trait_id in source_traits:
        for key in source.traitPropertyKeys(trait_id):
            value = source.getTraitProperty(trait_id, key)
            # Value is guaranteed non-None because we only iterate keys that
            # traitPropertyKeys reported as set.
            target.setTraitProperty(trait_id, key, value)  # pyright: ignore[reportArgumentType]
