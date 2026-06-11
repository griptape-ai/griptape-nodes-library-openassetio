# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Traits node for Griptape Nodes."""

from __future__ import annotations

import enum
import logging
from typing import TYPE_CHECKING, Any

from griptape_nodes.exe_types.core_types import BaseNodeElement, Parameter, ParameterGroup, ParameterMode
from griptape_nodes.exe_types.node_types import DataNode, NodeDependencies
from griptape_nodes.exe_types.param_components.parameter_transition_component import (
    ParameterTransitionComponent,
    TransitionParameter,
)
from griptape_nodes.node_library.library_registry import LibraryRegistry
from griptape_nodes.retained_mode.events.parameter_events import AddParameterToNodeRequest
from griptape_nodes.traits.multi_options import MultiOptions
from griptape_nodes.traits.options import Options
from openassetio.trait import TraitsData

from griptape_nodes_library_openassetio.trait_catalogue import TraitCatalogue, env_var_trait_definition_paths

if TYPE_CHECKING:
    from collections.abc import Callable

    from griptape_nodes_library_openassetio.trait_catalogue import TraitDefinition

logger = logging.getLogger(__name__)


class TraitUsage(enum.StrEnum):
    """Usage contexts for OpenAssetIO traits.

    Values match the ``usage`` enum in the OpenAssetIO trait schema.
    """

    ENTITY = "entity"
    LOCALE = "locale"
    RELATIONSHIP = "relationship"
    # Possibly not needed:
    # MANAGEMENT_POLICY = "managementPolicy"
    # UI = "ui"
    # UI_POLICY = "uiPolicy"


class Traits(DataNode):
    """Build, extract, and mutate OpenAssetIO TraitsData objects.

    The universal adapter between the OpenAssetIO trait system and Griptape Nodes
    wiring. Select traits/specifications via a multi-select picker to expose individual
    property parameters. At runtime, builds a ``TraitsData`` by merging upstream data
    with user overrides.

    Each trait property becomes an input+output parameter that can receive wired values
    (overrides) and passes through the final value to downstream nodes.
    """

    def __init__(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialise the node and register its static parameters.

        :param name: Node name.
        :param metadata: Additional metadata to merge with node defaults.
        """
        node_metadata = {
            "category": "OpenAssetIO",
            "description": "Build and mutate OpenAssetIO TraitsData",
        }
        if metadata:
            node_metadata.update(metadata)
        super().__init__(name=name, metadata=node_metadata)

        self._transition_component = ParameterTransitionComponent(
            self,
            manages_parameter=_is_dynamic_parameter,
        )

        self._trait_catalogue = _get_trait_catalogue(node_metadata)

        self.add_parameter(
            Parameter(
                name="traits_data_in",
                input_types=["TraitsData"],
                tooltip="Optional upstream TraitsData to merge",
                allowed_modes={ParameterMode.INPUT},
                serializable=False,
            )
        )
        self.add_parameter(
            Parameter(
                name="usage",
                type="str",
                default_value=TraitUsage.ENTITY.value,
                tooltip="Filter trait picker by usage context",
                allowed_modes={ParameterMode.PROPERTY},
                traits={Options(choices=[u.value for u in TraitUsage])},
            )
        )
        self.add_parameter(
            Parameter(
                name="trait_ids",
                type="list",
                default_value=[],
                tooltip="Traits to expose/imbue",
                allowed_modes={ParameterMode.PROPERTY},
                traits={
                    MultiOptions(
                        choices=self._trait_catalogue.choosable_ids_for_usage(
                            TraitUsage.ENTITY.value,
                        ),
                        show_search=True,
                        allow_user_created_options=False,
                    ),
                },
            )
        )
        self.add_parameter(
            Parameter(
                name="traits_data_out",
                output_type="TraitsData",
                tooltip="Complete TraitsData with all values",
                allowed_modes={ParameterMode.OUTPUT},
                serializable=False,
            )
        )
        output_trait_ids_group = ParameterGroup(name="Output Trait IDs", collapsed=True)
        output_trait_ids_param = Parameter(
            name="output_trait_ids",
            type="str",
            tooltip="All trait IDs in the output TraitsData (including propertyless)",
            allowed_modes={ParameterMode.PROPERTY},
            settable=False,
            serializable=False,
            ui_options={"multiline": True},
        )
        output_trait_ids_group.add_child(output_trait_ids_param)
        self.add_node_element(output_trait_ids_group)

    def after_value_set(self, parameter: Parameter, value: Any) -> None:  # noqa: ANN401
        """Rebuild dynamic parameters when trait_ids or usage changes.

        When ``usage`` changes, the ``trait_ids`` picker choices are updated to show
        only traits matching the new usage and any stale selections are cleared. When
        ``trait_ids`` changes, the dynamic property parameters are rebuilt.

        :param parameter: The parameter whose value changed.
        :param value: The new value.
        """
        if parameter.name == "usage":
            self._update_trait_ids_choices(value if isinstance(value, str) else TraitUsage.ENTITY.value)
        if parameter.name == "trait_ids":
            self._rebuild_dynamic_params(value if isinstance(value, list) else [])
        super().after_value_set(parameter, value)

    def validate_before_workflow_run(self) -> list[Exception] | None:
        """Warn when selected traits are absent from the current trait catalogue.

        A workflow saved against one set of trait definitions may be loaded in an
        environment where ``OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS`` (or the files it
        points at) differ. Selected traits missing from the current catalogue are
        silently dropped at runtime, so emit a warning naming them. This check is
        non-blocking; it returns the base class validation result unchanged.

        :returns: The base class validation result (unchanged).
        """
        selected_ids: list[str] = self.get_parameter_value("trait_ids") or []
        usage: str = self.get_parameter_value("usage")
        unknown_ids = self._trait_catalogue.unknown_ids_for_usage(selected_ids, usage)
        if unknown_ids:
            logger.warning(
                "Traits node '%s': %d selected trait/specification ID(s) are not available in the current trait"
                " catalogue and will be ignored: %s. Check that OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS matches the"
                " environment this workflow was created in.",
                self.name,
                len(unknown_ids),
                ", ".join(unknown_ids),
            )
        return super().validate_before_workflow_run()

    def get_node_dependencies(self) -> NodeDependencies | None:
        """Declare the trait definition files this node depends on.

        Custom trait definitions supplied via ``OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS``
        live outside the workflow, so declare them as static file dependencies. This
        records them with the serialized workflow and lets the packager bundle those
        that resolve under the project root, improving portability across environments.
        The built-in ``openassetio-mediacreation`` traits are covered by the library's
        pip dependencies and are not declared here.

        :returns: The aggregated dependencies, or ``None`` when there are none.
        """
        deps = super().get_node_dependencies()
        if deps is None:
            deps = NodeDependencies()

        for path in env_var_trait_definition_paths():
            deps.static_files.add(str(path))

        # Preserve the base contract of returning None when there is nothing to declare.
        if deps == NodeDependencies():
            return None
        return deps

    def process(self) -> None:
        """Build a TraitsData from the selected traits, upstream data, and overrides."""
        selected_ids: list[str] = self.get_parameter_value("trait_ids")
        # Optional input TraitsData to copy and extend.
        traits_data_in: TraitsData | None = self.get_parameter_value("traits_data_in")
        usage: str = self.get_parameter_value("usage")
        # Expand any specification IDs to their constituent trait IDs.
        expanded_ids = self._trait_catalogue.expand_to_trait_ids_for_usage(selected_ids, usage)
        # Copy-construct from upstream if available, else construct a blank TraitsData.
        traits_data_out = TraitsData(traits_data_in) if traits_data_in is not None else TraitsData()
        # Add any missing selected traits.
        traits_data_out.addTraits(set(expanded_ids))
        # Update output TraitsData with user overrides and collect final output parameters.
        for trait_id in expanded_ids:
            defn = self._trait_catalogue.get_trait(trait_id)
            if defn is None:
                continue
            for prop_name in defn.properties:
                param_name = f"{trait_id}.{prop_name}"
                # Use parameter_values directly (rather than get_parameter_value()) for
                # easier unit testing, where self.parameters may not be populated with
                # dynamic parameters.
                override_value = self.parameter_values.get(param_name)

                if override_value is not None:
                    # User override takes priority.
                    traits_data_out.setTraitProperty(trait_id, prop_name, override_value)

                self.parameter_output_values[param_name] = traits_data_out.getTraitProperty(trait_id, prop_name)

        self.parameter_output_values["traits_data_out"] = traits_data_out

        trait_set_out = sorted(traits_data_out.traitSet())
        self.set_parameter_value("output_trait_ids", "\n".join(trait_set_out))

    def _rebuild_dynamic_params(self, selected_ids: list[str]) -> None:
        """Transition dynamic parameters to match the selected trait IDs.

        Uses ``ParameterTransitionComponent`` to diff the current set of dynamic
        parameters against the desired set. Parameters whose type signature is unchanged
        are preserved in place (keeping their connections intact).

        :param selected_ids: List of trait IDs and/or specification IDs.
        """
        usage: str = self.get_parameter_value("usage")
        expanded_trait_ids = self._trait_catalogue.expand_to_trait_ids_for_usage(selected_ids, usage)

        desired_params = self._build_desired_params(expanded_trait_ids)

        self._transition_component.transition_to(desired_params)

        self._remove_stale_groups()

    def _update_trait_ids_choices(self, usage: str) -> None:
        """Replace the ``trait_ids`` picker choices and clear stale selections.

        Called when the ``usage`` dropdown changes. Any previously selected trait IDs
        that do not belong to the new usage are removed.

        :param usage: The new usage string.
        """
        new_choices = self._trait_catalogue.choosable_ids_for_usage(usage)
        trait_ids_param = self.get_parameter_by_name("trait_ids")
        if trait_ids_param is None:
            return

        # ui_options returns a shallow copy — nested dicts are shared
        # references into _ui_options.  Mutating them in place defeats the
        # old != new check in emits_update_on_write, so build a fresh dict.
        multi_options = {**trait_ids_param.ui_options.get("multi_options", {}), "choices": new_choices}
        trait_ids_param.update_ui_options_key("multi_options", multi_options)

        # Remove stale selections that no longer appear in the new choices.
        valid = set(new_choices)
        current: list[str] = self.get_parameter_value("trait_ids")
        pruned = [tid for tid in current if tid in valid]
        if pruned != current:
            self.set_parameter_value("trait_ids", pruned)

    def _build_desired_params(
        self,
        expanded_trait_ids: list[str],
    ) -> list[TransitionParameter]:
        """Build desired parameters and ensure the group hierarchy exists.

        For each trait, ensures the package > namespace > member group hierarchy is
        present on the node, then builds ``TransitionParameter`` descriptors for each
        property. Unlike ``ResolveEntity``, these parameters have both INPUT and OUTPUT
        modes so users can wire in override values.

        :param expanded_trait_ids: Fully expanded list of trait IDs.

        :returns: List of desired TransitionParameters.
        """
        desired_params: list[TransitionParameter] = []

        for trait_id in expanded_trait_ids:
            defn = self._trait_catalogue.get_trait(trait_id)
            if defn is None:
                continue

            self._ensure_trait_groups_exist(defn)

            for prop_name, prop in defn.properties.items():
                param_type = _TRAIT_TYPE_TO_PARAM_TYPE.get(prop.type, "str")
                param_name = f"{trait_id}.{prop_name}"

                desired_params.append(
                    TransitionParameter(
                        name=param_name,
                        allowed_modes=frozenset({ParameterMode.INPUT, ParameterMode.OUTPUT}),
                        input_types=frozenset({param_type}),
                        output_type=param_type,
                        add_request_factory=self._make_trait_property_param_request_factory(
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
        """Create the package > namespace > member group hierarchy for a trait.

        Each level is only created if it doesn't already exist on the node.

        :param defn: The trait definition whose groups must exist.
        """
        # Package group.
        pkg_group_elem = self.get_group_by_name_or_element_id(defn.package)
        if pkg_group_elem is None:
            pkg_group_elem = ParameterGroup(
                name=defn.package,
                user_defined=True,
                ui_options={"display_name": defn.package},
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
            )
            pkg_group_elem.add_child(ns_group_elem)

        # Member group: the trait ID itself.
        if self.get_group_by_name_or_element_id(defn.trait_id) is None:
            member_group = ParameterGroup(
                name=defn.trait_id,
                user_defined=True,
                ui_options={"display_name": _trait_group_display_name(defn)},
            )
            ns_group_elem.add_child(member_group)

    def _emit_parameter_lifecycle_event(self, parameter: BaseNodeElement, *, remove: bool = False) -> None:
        """Set info badges on dynamic elements as they are added to the node.

        Every path that adds an element - ``add_node_element``, ``add_child``, and the
        engine's deserialization handler - converges on this hook. Setting badges here
        rather than at each call-site ensures dynamic elements always carry their
        catalogue description regardless of how they were created.

        In particular, badges on dynamic parameters are not serialised with the workflow
        so setting them the normal way means the badges disappear after a save/load. We
        work around the problem by overriding this hook instead, which runs whether
        deserialising or through UI changes.

        :param parameter: The element being added or removed.
        :param remove: True when the element is being removed.
        """
        super()._emit_parameter_lifecycle_event(parameter, remove=remove)
        if remove:
            return
        if not getattr(parameter, "user_defined", False):
            return
        if parameter.get_badge() is not None:
            return
        message = self._badge_message_for_element(parameter)
        if message:
            parameter.set_badge(variant="info", message=message)

    def _badge_message_for_element(self, element: BaseNodeElement) -> str:
        """Look up the badge description for a dynamic element from the catalogue.

        For ``ParameterGroup`` elements the name encodes the hierarchy level (package,
        namespace, or member/trait), and the corresponding catalogue method is called.
        For ``Parameter`` elements the tooltip already contains the property description
        and is used directly.

        :param element: The element to look up.

        :returns: The description text, or ``""`` if no description is available.
        """
        if isinstance(element, Parameter) and isinstance(element.tooltip, str):
            return element.tooltip
        if isinstance(element, ParameterGroup):
            catalogue = self._trait_catalogue
            # Member group (trait ID).
            defn = catalogue.get_trait(element.name)
            if defn is not None:
                return defn.description
            # Namespace group ("package:namespace").
            ns_desc = catalogue.get_namespace_description(element.name)
            if ns_desc:
                return ns_desc
            # Package group.
            return catalogue.get_package_description(element.name)
        return ""

    def _make_trait_property_param_request_factory(
        self,
        *,
        param_name: str,
        param_type: str,
        tooltip: str,
        parent_element_name: str,
        display_name: str,
    ) -> Callable[[], AddParameterToNodeRequest]:
        """Create a factory that builds an AddParameterToNodeRequest for a trait property.

        :param param_name: Full parameter name (e.g. "trait_id.property").
        :param param_type: Griptape type string (str, int, float, bool).
        :param tooltip: Tooltip description text.
        :param parent_element_name: Qualified name of the parent ParameterGroup.
        :param display_name: Human-readable display name for the parameter.

        :returns: A callable that produces the AddParameterToNodeRequest.
        """

        def factory() -> AddParameterToNodeRequest:
            return AddParameterToNodeRequest(
                node_name=self.name,
                parameter_name=param_name,
                input_types=[param_type],
                output_type=param_type,
                tooltip=tooltip,
                mode_allowed_input=True,
                mode_allowed_property=False,
                mode_allowed_output=True,
                is_user_defined=True,
                parent_element_name=parent_element_name,
                ui_options={"display_name": display_name, "placeholder_text": "(not set)"},
            )

        return factory

    def _remove_stale_groups(self) -> None:
        """Remove dynamic groups that no longer contain any parameters.

        After the transition component has removed stale parameters, any group with no
        ``Parameter`` descendants is empty and should be cleaned up.
        """
        # noinspection PyTypeChecker
        pkg_groups: list[ParameterGroup] = [
            child for child in self.root_ui_element.children if isinstance(child, ParameterGroup) and child.user_defined
        ]
        for pkg_group in pkg_groups:
            if not _has_parameter_descendant(pkg_group):
                self.remove_parameter_element_by_name(pkg_group.name)
                continue
            _prune_empty_groups(pkg_group)


def _get_trait_catalogue(metadata: dict[str, Any]) -> TraitCatalogue:
    """Look up the shared :class:`TraitCatalogue` from the library registry.

    Returns an empty :class:`TraitCatalogue` when the ``"library"`` key is absent — this
    happens when the engine constructs a bare reference node during serialization.

    :param metadata: The node's metadata dict.

    :returns: The shared :class:`TraitCatalogue`, or an empty one if the library key is
        missing.
    """
    library_name: str | None = metadata.get("library")
    if not library_name:
        return TraitCatalogue({})

    library = LibraryRegistry.get_library(library_name)
    hooks = library.get_advanced_library()
    return hooks.trait_catalogue  # type: ignore[union-attr,attr-defined]


def _is_dynamic_parameter(param: Parameter) -> bool:
    """Predicate: True for parameters managed by the transition component.

    Dynamic parameters are marked ``user_defined=True``, indicating they were added at
    runtime rather than in ``__init__``.

    :param param: The parameter to check.

    :returns: True if this is a dynamic parameter.
    """
    return param.user_defined


def _trait_group_display_name(defn: TraitDefinition) -> str:
    """Compute the human-readable member group display name for a trait.

    v1 uses just the member name; v2+ appends "(v{n})".

    :param defn: The trait definition.

    :returns: The display name string.
    """
    if defn.version == "1":
        return defn.member_name
    return f"{defn.member_name} (v{defn.version})"


def _has_parameter_descendant(group: ParameterGroup) -> bool:
    """Return True if *group* contains at least one Parameter in its subtree.

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

    :param group: The parent group to prune children from.
    """
    for child in list(group.children):
        if not isinstance(child, ParameterGroup):
            continue
        _prune_empty_groups(child)
        if not _has_parameter_descendant(child):
            group.remove_child(child)


# Maps traits.yml type names to Griptape parameter type strings.
_TRAIT_TYPE_TO_PARAM_TYPE: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
}
