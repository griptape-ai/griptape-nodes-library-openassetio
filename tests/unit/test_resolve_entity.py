# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for resolve_entity business logic."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from griptape_nodes_library_openassetio.session import ManagerSession
from openassetio import Context
from openassetio.access import ResolveAccess
from openassetio.hostApi import HostInterface, Manager
from openassetio.trait import TraitsData


def _make_session() -> tuple[ManagerSession, Mock]:
    """Build a mock ManagerSession and return it alongside the mock manager."""
    mock_manager = Mock(spec=Manager)
    session = ManagerSession(
        manager=mock_manager,
        context=Mock(spec=Context),
        host_interface=Mock(spec=HostInterface),
    )
    return session, mock_manager


class TestResolveEntity:
    """Tests for the resolve_entity() function."""

    def test_returns_resolved_property_values(self) -> None:
        session, mock_manager = _make_session()

        mock_traits_data = Mock(spec=TraitsData)
        mock_traits_data.traitSet.return_value = {"test:content.LocatableContent"}
        mock_traits_data.traitPropertyKeys.return_value = {"location", "mimeType"}
        mock_traits_data.getTraitProperty.side_effect = lambda tid, key: {
            ("test:content.LocatableContent", "location"): "file:///path/to/file.exr",
            ("test:content.LocatableContent", "mimeType"): "image/x-exr",
        }[tid, key]

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = mock_traits_data

        results = resolve_entity(session, "asset://my/entity", {"test:content.LocatableContent"})

        assert results == {
            "test:content.LocatableContent.location": "file:///path/to/file.exr",
            "test:content.LocatableContent.mimeType": "image/x-exr",
        }

    def test_creates_entity_reference_from_string(self) -> None:
        session, mock_manager = _make_session()
        mock_traits_data = Mock(spec=TraitsData)
        mock_traits_data.traitSet.return_value = set()
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = mock_traits_data

        resolve_entity(session, "asset://my/entity", {"test:ns.Trait"})

        mock_manager.createEntityReference.assert_called_once_with("asset://my/entity")

    def test_passes_trait_ids_and_context_to_resolve(self) -> None:
        session, mock_manager = _make_session()
        mock_traits_data = Mock(spec=TraitsData)
        mock_traits_data.traitSet.return_value = set()
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = mock_traits_data

        trait_ids = {"test:content.LocatableContent", "test:identity.DisplayName"}
        resolve_entity(session, "asset://my/entity", trait_ids)

        mock_manager.resolve.assert_called_once_with("ref_obj", trait_ids, ResolveAccess.kRead, session.context)

    def test_returns_empty_dict_when_no_traits_resolved(self) -> None:
        session, mock_manager = _make_session()
        mock_traits_data = Mock(spec=TraitsData)
        mock_traits_data.traitSet.return_value = set()
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = mock_traits_data

        results = resolve_entity(session, "asset://my/entity", {"test:ns.Trait"})

        assert results == {}

    def test_propagates_resolve_exception(self) -> None:
        """Exceptions from manager.resolve() propagate to the caller."""
        session, mock_manager = _make_session()
        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.side_effect = RuntimeError("Entity not found")

        with pytest.raises(RuntimeError, match="Entity not found"):
            resolve_entity(session, "asset://missing", {"test:ns.Trait"})

    def test_handles_multiple_traits(self) -> None:
        session, mock_manager = _make_session()
        mock_traits_data = Mock(spec=TraitsData)
        mock_traits_data.traitSet.return_value = {
            "test:content.LocatableContent",
            "test:identity.DisplayName",
        }
        mock_traits_data.traitPropertyKeys.side_effect = lambda tid: {
            "test:content.LocatableContent": {"location"},
            "test:identity.DisplayName": {"name"},
        }[tid]
        mock_traits_data.getTraitProperty.side_effect = lambda tid, key: {
            ("test:content.LocatableContent", "location"): "file:///image.png",
            ("test:identity.DisplayName", "name"): "My Entity",
        }[tid, key]

        mock_manager.createEntityReference.return_value = "ref_obj"
        mock_manager.resolve.return_value = mock_traits_data

        results = resolve_entity(
            session,
            "asset://my/entity",
            {"test:content.LocatableContent", "test:identity.DisplayName"},
        )

        assert results["test:content.LocatableContent.location"] == "file:///image.png"
        assert results["test:identity.DisplayName.name"] == "My Entity"
