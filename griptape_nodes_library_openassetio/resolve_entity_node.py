# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""ResolveEntity node for Griptape Nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from griptape_nodes.exe_types.core_types import BadgeData, Parameter, ParameterGroup, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode
from griptape_nodes.exe_types.param_components.parameter_transition_component import (
    ParameterTransitionComponent,
    TransitionParameter,
)
from griptape_nodes.node_library.library_registry import LibraryRegistry
from griptape_nodes.retained_mode.events.parameter_events import AddParameterToNodeRequest
from griptape_nodes.traits.multi_options import MultiOptions
from openassetio.errors import OpenAssetIOException

from griptape_nodes_library_openassetio.resolve_entity import resolve_entity
from griptape_nodes_library_openassetio.session import ManagerSession
from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes_library_openassetio.trait_catalogue import TraitDefinition

# Maps traits.yml type names to Griptape parameter type strings.
_TRAIT_TYPE_TO_PARAM_TYPE: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
}


class ResolveEntity(SuccessFailureNode):
    """Resolve an entity reference and output its trait property values.

    Takes an entity reference string and a selection of trait IDs, then calls
    ``manager.resolve()`` to fetch property values from the asset manager. Each trait
    property becomes an individual output parameter that can be wired to downstream
    nodes.

    .. note::

        Output parameters whose trait properties are not populated by the asset manager
        remain ``None`` after execution. A downstream node connected to such a parameter
        will receive ``None``. This is valid — not every entity has a value for every
        property in a trait.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its static parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Resolve an entity reference and output trait properties",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        # Component that diffs current vs desired dynamic parameters, preserving
        # connections when a parameter's type signature hasn't changed.
        self._transition_component = ParameterTransitionComponent(
            self,
            manages_parameter=_is_dynamic_output_parameter,
        )

        # Retrieve the shared catalogue built at library load time by
        # LibraryHooks.before_library_nodes_loaded(). Returns an empty
        # catalogue when the engine constructs a bare reference node
        # during serialization.
        self._trait_catalogue = _get_trait_catalogue(node_metadata)

        self.add_parameter(
            Parameter(
                name="session",
                input_types=["ManagerSession"],
                tooltip="Session from an OpenAssetIOSession node",
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="entity_reference",
                type="str",
                default_value="",
                tooltip="Entity reference to resolve (e.g. asset://project/sequence/shot)",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="trait_ids",
                type="list",
                default_value=[],
                tooltip="Entity traits to resolve",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
                traits={
                    MultiOptions(
                        choices=self._trait_catalogue.all_choosable_ids(),
                        show_search=True,
                        allow_user_created_options=False,
                    ),
                },
            )
        )

        self._create_status_parameters(
            result_details_tooltip="Details about the resolve operation result",
            result_details_placeholder="Resolve result will be shown here.",
        )

    def after_value_set(self, parameter: Parameter, value: Any) -> None:  # noqa: ANN401
        """Rebuild the dynamic output tree when trait_ids changes.

        :param parameter: The parameter whose value changed.
        :param value: The new value.
        """
        if parameter.name == "trait_ids":
            self._rebuild_dynamic_outputs(value if isinstance(value, list) else [])
        return super().after_value_set(parameter, value)

    def process(self) -> None:
        """Resolve the entity reference and populate output parameters."""
        self._clear_execution_status()

        session: ManagerSession | None = self.parameter_values.get("session")
        if not isinstance(session, ManagerSession):
            self._set_status_results(
                was_successful=False,
                result_details="FAILURE: No session connected",
            )
            self._handle_failure_exception(ValueError("No session connected. Connect an OpenAssetIOSession node"))
            return

        entity_reference: str | None = self.parameter_values.get("entity_reference")
        if not entity_reference:
            self._set_status_results(
                was_successful=False,
                result_details="FAILURE: No entity reference provided",
            )
            self._handle_failure_exception(ValueError("No entity reference provided"))
            return

        selected_ids: list[str] = self.parameter_values.get("trait_ids", [])
        if not selected_ids:
            self._set_status_results(
                was_successful=False,
                result_details="FAILURE: No trait IDs selected",
            )
            self._handle_failure_exception(ValueError("No trait IDs selected"))
            return

        expanded_trait_ids = self._trait_catalogue.expand_to_resolvable_trait_ids(selected_ids)

        try:
            results = resolve_entity(session, entity_reference, set(expanded_trait_ids))
        except (RuntimeError, OpenAssetIOException) as exc:
            self._set_status_results(
                was_successful=False,
                result_details=f"FAILURE: {exc}",
            )
            self._handle_failure_exception(exc)
            return

        # Clear all dynamic output values before populating new results.
        # Without this, properties resolved in a previous run but absent from
        # the current resolve would retain their stale values.
        for trait_id in expanded_trait_ids:
            defn = self._trait_catalogue.get_trait(trait_id)
            if defn is None:
                continue
            for prop_name in defn.properties:
                self.parameter_output_values[f"{trait_id}.{prop_name}"] = None

        for param_name, value in results.items():
            self.parameter_output_values[param_name] = value

        self._set_status_results(
            was_successful=True,
            result_details=f"SUCCESS: Resolved {entity_reference}",
        )

    def _rebuild_dynamic_outputs(self, selected_ids: list[str]) -> None:
        """Transition dynamic outputs to match the selected trait IDs.

        Uses ``ParameterTransitionComponent`` to diff the current set of dynamic output
        parameters against the desired set. Parameters whose type signature is unchanged
        are preserved in place (keeping their connections intact). Parameters that are
        new or have a changed signature are added/replaced via the engine event system,
        which re-creates compatible connections automatically.

        Groups (package > namespace > member) are managed separately: stale groups are
        removed after the parameter transition, and new groups are created before
        parameters that need them are added.

        :param selected_ids: List of trait IDs and/or specification IDs.
        """
        expanded_trait_ids = self._trait_catalogue.expand_to_resolvable_trait_ids(selected_ids)

        # Build the desired parameters, creating any missing groups along the way.
        desired_params = self._build_desired_params(expanded_trait_ids)

        # Let the transition component diff and apply changes, preserving
        # connections on unchanged parameters.
        self._transition_component.transition_to(desired_params)

        # Set badges on newly created dynamic output parameters. The tooltip
        # already holds the property description; reuse it as the badge message.
        self._apply_badges_to_dynamic_params()

        # Remove groups that are no longer needed (they are now empty).
        self._remove_stale_groups()

    def _build_desired_params(
        self,
        expanded_trait_ids: list[str],
    ) -> list[TransitionParameter]:
        """Build desired parameters and ensure the group hierarchy exists.

        For each trait, ensures the package → namespace → member group hierarchy is
        present on the node, then builds ``TransitionParameter`` descriptors for each
        property. Group names are derived from the trait ID structure:

        - Package: ``"openassetio-mediacreation"``
        - Namespace: ``"openassetio-mediacreation:content"``
        - Member: ``"openassetio-mediacreation:content.LocatableContent"`` (the trait ID
          itself)

        These are structurally unambiguous (no ``:`` in packages, no ``.`` before the
        member in namespace IDs), so collisions are impossible. The human-readable label
        is stored in ``ui_options.display_name``.

        :param expanded_trait_ids: Fully expanded list of resolvable trait IDs.

        :returns: List of desired TransitionParameters.
        """
        desired_params: list[TransitionParameter] = []

        for trait_id in expanded_trait_ids:
            defn = self._trait_catalogue.get_trait(trait_id)
            # Traits not in the catalogue have no known properties, so there is
            # nothing to display. The user cannot enter custom IDs
            # (allow_user_created_options is False), so this can only arise from
            # a stale saved workflow.
            if defn is None:
                continue

            self._ensure_trait_groups_exist(defn)

            for prop_name, prop in defn.properties.items():
                param_type = _TRAIT_TYPE_TO_PARAM_TYPE.get(prop.type, "str")
                param_name = f"{trait_id}.{prop_name}"

                desired_params.append(
                    TransitionParameter(
                        name=param_name,
                        allowed_modes=frozenset({ParameterMode.OUTPUT}),
                        input_types=frozenset(),
                        output_type=param_type,
                        add_request_factory=_make_add_request_factory(
                            node_name=self.name,
                            param_name=param_name,
                            param_type=param_type,
                            tooltip=prop.description,
                            parent_element_name=trait_id,
                            display_name=prop_name,
                        ),
                    )
                )

        return desired_params

    def _ensure_trait_groups_exist(self, defn: TraitDefinition) -> None:
        """Create the package → namespace → member group hierarchy for a trait.

        Each level is only created if it doesn't already exist on the node. Every group
        receives an info badge with the corresponding description from the trait
        catalogue (package, namespace, or trait level).

        :param defn: The trait definition whose groups must exist.
        """
        catalogue = self._trait_catalogue

        # Package group.
        pkg_group_elem = self.get_group_by_name_or_element_id(defn.package)
        if pkg_group_elem is None:
            pkg_group_elem = ParameterGroup(
                name=defn.package,
                user_defined=True,
                ui_options={"display_name": defn.package},
                badge=_make_info_badge(catalogue.get_package_description(defn.package)),
            )
            self.add_node_element(pkg_group_elem)

        # Namespace group: "package:namespace".
        ns_group_name = f"{defn.package}:{defn.namespace}"
        ns_group_elem = self.get_group_by_name_or_element_id(ns_group_name)
        if ns_group_elem is None:
            ns_group_elem = ParameterGroup(
                name=ns_group_name,
                user_defined=True,
                ui_options={"display_name": defn.namespace},
                badge=_make_info_badge(catalogue.get_namespace_description(ns_group_name)),
            )
            pkg_group_elem.add_child(ns_group_elem)

        # Member group: the trait ID itself.
        if self.get_group_by_name_or_element_id(defn.trait_id) is None:
            member_group = ParameterGroup(
                name=defn.trait_id,
                user_defined=True,
                ui_options={"display_name": _trait_group_display_name(defn)},
                badge=_make_info_badge(defn.description),
            )
            ns_group_elem.add_child(member_group)

    def _apply_badges_to_dynamic_params(self) -> None:
        """Set info badges on all dynamic output parameters.

        Each dynamic parameter already carries the property description as its tooltip;
        this method reuses that text as the badge message.

        Note that at time of writing, tooltips on Parameters in nested ParameterGroups
        don't show up (bug reported upstream), so the badge is the only way of surfacing
        this information.
        """
        for param in self.parameters:
            # Dynamic output tooltips are always plain strings (set via
            # AddParameterToNodeRequest), so the isinstance check is a
            # type-narrowing guard for pyright.
            if _is_dynamic_output_parameter(param) and param.get_badge() is None and isinstance(param.tooltip, str):
                param.set_badge(variant="info", message=param.tooltip)

    def _remove_stale_groups(self) -> None:
        """Remove dynamic groups that no longer contain any parameters.

        After the transition component has removed stale parameters, any group with no
        ``Parameter`` descendants is empty and should be cleaned up. We walk bottom-up:
        member groups first, then namespace groups, then package groups — removing each
        if it has no remaining children.
        """
        # Dynamic package groups are user_defined ParameterGroups at the root level.
        # noinspection PyTypeChecker
        pkg_groups: list[ParameterGroup] = [
            child for child in self.root_ui_element.children if isinstance(child, ParameterGroup) and child.user_defined
        ]
        for pkg_group in pkg_groups:
            if not _has_parameter_descendant(pkg_group):
                # Package is completely empty — remove it entirely.
                self.remove_parameter_element_by_name(pkg_group.name)
                continue
            # Package still has parameters — prune empty inner groups.
            _prune_empty_groups(pkg_group)


def _get_trait_catalogue(metadata: dict[str, Any]) -> TraitCatalogue:
    """Look up the shared :class:`TraitCatalogue` from the library registry.

    The catalogue is built once at library load time by :class:`LibraryHooks` and stored
    on the ``Library`` object. Nodes retrieve it via the ``metadata["library"]`` key
    injected by the engine's ``Library.create_node()`` method.

    Returns an empty :class:`TraitCatalogue` when the ``"library"`` key is absent — this
    happens when the engine constructs a bare reference node during serialization (via
    ``type(node)(name="REFERENCE NODE")``).

    :param metadata: The node's metadata dict.

    :returns: The shared :class:`TraitCatalogue`, or an empty one if the library key is
        missing.
    """
    library_name: str | None = metadata.get("library")
    if not library_name:
        return TraitCatalogue({})

    library = LibraryRegistry.get_library(library_name)
    # Access .trait_catalogue via duck-typing rather than isinstance(hooks, LibraryHooks). The
    # engine loads library_hooks.py via importlib with a dynamic module name
    # (gtn_dynamic_module_*), producing a different class identity to our normal import
    # of LibraryHooks. The attribute is invariant at runtime — the engine aborts library
    # registration if the AdvancedNodeLibrary fails to load, so nodes are never
    # constructed without it.
    hooks = library.get_advanced_library()
    return hooks.trait_catalogue  # type: ignore[union-attr,attr-defined]


def _is_dynamic_output_parameter(param: Parameter) -> bool:
    """Predicate: True for parameters managed by the transition component.

    Dynamic output parameters are marked ``user_defined=True`` — this flag (despite the
    name) indicates a parameter that was added at runtime rather than in ``__init__``,
    and must be serialized into the workflow JSON to survive save/load. All our static
    params (session, entity_reference, trait_ids) and the SuccessFailureNode status
    params leave it as False.

    :param param: The parameter to check.

    :returns: True if this is a dynamic output parameter.
    """
    return param.user_defined


def _make_info_badge(message: str) -> BadgeData:
    """Create an info badge with the given description message.

    :param message: The badge message text.

    :returns: A :class:`BadgeData` with variant ``"info"``.
    """
    return BadgeData(variant="info", message=message)


def _trait_group_display_name(defn: TraitDefinition) -> str:
    """Compute the human-readable member group display name for a trait.

    v1 uses just the member name; v2+ appends "(v{n})" to disambiguate while remaining
    human-readable.

    :param defn: The trait definition.

    :returns: The display name string.
    """
    if defn.version == "1":
        return defn.member_name
    return f"{defn.member_name} (v{defn.version})"


def _has_parameter_descendant(group: ParameterGroup) -> bool:
    """Return True if *group* contains at least one Parameter anywhere in its subtree.

    :param group: The group to search.

    :returns: True if a Parameter exists under this group.
    """
    for child in group.children:
        if isinstance(child, Parameter):
            return True
        if isinstance(child, ParameterGroup) and _has_parameter_descendant(child):
            return True
    return False


def _prune_empty_groups(group: ParameterGroup) -> None:
    """Recursively remove child ParameterGroups that have no Parameter descendants.

    Walks depth-first so that leaf groups are removed before their parents are checked.

    :param group: The parent group to prune children from.
    """
    for child in list(group.children):
        if not isinstance(child, ParameterGroup):
            continue
        # Recurse first so inner empties are removed before we check this level.
        _prune_empty_groups(child)
        if not _has_parameter_descendant(child):
            group.remove_child(child)


def _make_add_request_factory(  # noqa: PLR0913
    *,
    node_name: str,
    param_name: str,
    param_type: str,
    tooltip: str,
    parent_element_name: str,
    display_name: str,
) -> Callable[[], AddParameterToNodeRequest]:
    """Create a factory that builds an AddParameterToNodeRequest.

    The factory is deferred (a closure) because the ``ParameterTransitionComponent``
    only calls it when the parameter actually needs to be created.

    :param node_name: Name of the node to add the parameter to.
    :param param_name: Full parameter name (e.g. "trait_id.property").
    :param param_type: Griptape type string (str, int, float, bool).
    :param tooltip: Tooltip description text.
    :param parent_element_name: Qualified name of the parent ParameterGroup.
    :param display_name: Human-readable display name for the parameter.

    :returns: A callable that produces the AddParameterToNodeRequest.
    """

    def factory() -> AddParameterToNodeRequest:
        return AddParameterToNodeRequest(
            node_name=node_name,
            parameter_name=param_name,
            output_type=param_type,
            tooltip=tooltip,
            mode_allowed_input=False,
            mode_allowed_property=False,
            mode_allowed_output=True,
            is_user_defined=True,
            parent_element_name=parent_element_name,
            ui_options={"display_name": display_name, "placeholder_text": "(unresolved)"},
        )

    return factory
