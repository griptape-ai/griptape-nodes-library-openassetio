# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Trait catalogue: loads and indexes trait definitions from traits.yml files."""

from __future__ import annotations

import dataclasses
import importlib.resources
import logging
import os
from pathlib import Path
from typing import Any

import yaml

_ENV_VAR = "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS"

_log = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class TraitProperty:
    """A single property within an OpenAssetIO trait definition.

    :param name: Property name (e.g. ``"location"``).
    :param type: Property type as declared in traits.yml (``"string"``, ``"integer"``,
        ``"float"``, ``"boolean"``).
    :param description: Human-readable description of the property.
    """

    name: str
    type: str
    description: str


@dataclasses.dataclass(frozen=True)
class TraitDefinition:
    """A single OpenAssetIO trait definition with its properties.

    :param trait_id: Fully-qualified trait ID (e.g.
        ``"openassetio-mediacreation:content.LocatableContent"``).
    :param package: Package name (e.g. ``"openassetio-mediacreation"``).
    :param namespace: Trait namespace (e.g. ``"content"``).
    :param member_name: Trait member name (e.g. ``"LocatableContent"``).
    :param description: Human-readable description of the trait.
    :param version: Version string from traits.yml (e.g. ``"1"``, ``"2"``).
    :param usage: List of usage contexts (e.g. ``["entity"]``, ``["relationship"]``).
    :param properties: Mapping of property name to :class:`TraitProperty`.
    """

    trait_id: str
    package: str
    namespace: str
    member_name: str
    description: str
    version: str
    usage: list[str]
    properties: dict[str, TraitProperty]


@dataclasses.dataclass(frozen=True)
class SpecificationDefinition:
    """A specification: a named set of traits that describes an asset type.

    :param spec_id: Fully-qualified specification ID.
    :param package: Package name.
    :param namespace: Specification namespace.
    :param member_name: Specification member name.
    :param description: Human-readable description.
    :param usage: List of usage contexts (e.g. ``["entity"]``).
    :param trait_ids: Ordered list of trait IDs in this specification.
    """

    spec_id: str
    package: str
    namespace: str
    member_name: str
    description: str
    usage: list[str]
    trait_ids: list[str]


class TraitCatalogue:
    """Index of trait and specification definitions from traits.yml files."""

    def __init__(
        self,
        traits: dict[str, TraitDefinition],
        specifications: dict[str, SpecificationDefinition] | None = None,
        *,
        package_descriptions: dict[str, str] | None = None,
        namespace_descriptions: dict[str, str] | None = None,
    ) -> None:
        """Initialise the catalogue.

        :param traits: Mapping of trait ID to :class:`TraitDefinition`.
        :param specifications: Mapping of spec ID to :class:`SpecificationDefinition`.
        :param package_descriptions: Mapping of package name to its human-readable
            description. Supports multiple trait packages.
        :param namespace_descriptions: Mapping of qualified namespace name
            (``"{package}:{namespace}"``) to its description string.
        """
        self._traits = traits
        self._specifications = specifications or {}
        self._package_descriptions = package_descriptions or {}
        self._namespace_descriptions = namespace_descriptions or {}

    def get_trait(self, trait_id: str) -> TraitDefinition | None:
        """Look up a trait definition by its fully-qualified ID.

        :param trait_id: The trait ID to look up.

        :returns: The trait definition, or ``None`` if not found.
        """
        return self._traits.get(trait_id)

    def get_specification(self, spec_id: str) -> SpecificationDefinition | None:
        """Look up a specification by its fully-qualified ID.

        :param spec_id: The specification ID to look up.

        :returns: The specification definition, or ``None`` if not found.
        """
        return self._specifications.get(spec_id)

    def get_package_description(self, package: str) -> str:
        """Look up a package description by name.

        :param package: Package name (e.g. ``"openassetio-mediacreation"``).

        :returns: The description string, or ``""`` if not found.
        """
        return self._package_descriptions.get(package, "")

    def get_namespace_description(self, qualified_name: str) -> str:
        """Look up a namespace description by its qualified name.

        :param qualified_name: Qualified namespace name in ``"{package}:{namespace}"``
            format.

        :returns: The description string, or ``""`` if not found.
        """
        return self._namespace_descriptions.get(qualified_name, "")

    def resolvable_trait_ids(self) -> list[str]:
        """Return a sorted list of entity trait IDs that have properties.

        Excludes traits with no properties (no resolvable outputs) and traits whose
        usage does not include ``"entity"``.

        :returns: Sorted list of trait ID strings.
        """
        return sorted(tid for tid, defn in self._traits.items() if defn.properties and "entity" in defn.usage)

    def all_choosable_ids(self) -> list[str]:
        """Return specification IDs then trait IDs suitable for a picker UI.

        Specifications appear first (sorted), followed by traits (sorted). Excluded:
        traits without properties, traits/specifications whose usage does not include
        ``"entity"``, and specifications that only reference propertyless traits.

        :returns: Ordered list of choosable ID strings.
        """
        trait_ids = set(self.resolvable_trait_ids())
        spec_ids = sorted(
            sid
            for sid, spec in self._specifications.items()
            if "entity" in spec.usage and any(tid in trait_ids for tid in spec.trait_ids)
        )
        return spec_ids + sorted(trait_ids)

    def expand_to_resolvable_trait_ids(self, selected_ids: list[str]) -> list[str]:
        """Expand a mixed list of trait and specification IDs to trait IDs.

        Specifications are replaced by their constituent trait IDs. Only traits that
        have properties and ``"entity"`` usage are included — propertyless traits from
        specifications are silently dropped since they produce no resolvable outputs.
        Duplicates are removed while preserving the order in which each trait ID first
        appears.

        :param selected_ids: List of trait IDs and/or specification IDs.

        :returns: Deduplicated list of trait IDs.
        """
        # Filter to exclude propertyless/non-entity traits.
        valid_trait_ids = set(self.resolvable_trait_ids())

        result: list[str] = []
        for selected_id in selected_ids:
            if spec := self._specifications.get(selected_id):
                # Specification ID.
                result.extend(spec.trait_ids)
            else:
                # Trait ID.
                result.append(selected_id)

        # Filter to ensure valid trait IDs, i.e. the trait exists, is an entity trait,
        # and has properties.
        result = [tid for tid in result if tid in valid_trait_ids]
        # De-dupe. Guaranteed order-preserving in Python 3.7+.
        return list(dict.fromkeys(result))


def load_default_catalogue() -> TraitCatalogue:
    """Build the default trait catalogue from disk.

    The catalogue is built from the ``traits.yml`` shipped with the
    ``openassetio_mediacreation`` package. If the
    :data:`OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS` environment variable is set, it is
    treated as an ``os.pathsep``-separated list of paths to additional traits YAML
    files. Each file is loaded in order and merged into the catalogue — later files
    override earlier ones for the same trait IDs, allowing users to add custom trait
    packages or overwrite the default ``openassetio-mediacreation`` package.

    A fresh catalogue is built on every call — no caching. This allows callers to
    control the lifecycle (e.g. rebuilding when a node is recreated or a library is
    reloaded).

    :returns: A new :class:`TraitCatalogue` instance.
    """
    yaml_sources = [_load_default_yaml(), *_load_env_var_yamls()]
    return build_catalogue_from_yaml_list(yaml_sources)


def build_catalogue_from_yaml_list(yaml_list: list[dict[str, Any]]) -> TraitCatalogue:
    """Build a single :class:`TraitCatalogue` from multiple parsed YAML dicts.

    Each YAML dict is processed in order. Later entries override earlier ones when trait
    IDs, specification IDs, package descriptions, or namespace descriptions collide.

    :param yaml_list: Ordered list of parsed traits YAML dicts, each with ``package``,
        ``traits``, and optionally ``specifications`` keys.

    :returns: A single merged :class:`TraitCatalogue`.
    """
    merged_traits: dict[str, TraitDefinition] = {}
    merged_specs: dict[str, SpecificationDefinition] = {}
    merged_pkg_descs: dict[str, str] = {}
    merged_ns_descs: dict[str, str] = {}

    for yaml_data in yaml_list:
        package = yaml_data.get("package", "")
        if not package:
            _log.warning("Skipping YAML entry with no 'package' key: %s", yaml_data)
            continue

        traits_section = yaml_data.get("traits", {})
        specs_section = yaml_data.get("specifications", {})

        # Validate that traits/specifications are dicts. User-supplied YAML
        # may provide these as a list, string, etc.
        if traits_section and not isinstance(traits_section, dict):
            _log.warning("Package '%s': 'traits' is not a mapping, skipping traits", package)
            traits_section = {}
        if specs_section and not isinstance(specs_section, dict):
            _log.warning("Package '%s': 'specifications' is not a mapping, skipping specifications", package)
            specs_section = {}

        if not traits_section and not specs_section:
            _log.warning("Package '%s' has no traits and no specifications", package)
            continue

        package_description = yaml_data.get("description", "")
        merged_traits.update(_build_traits(package, traits_section))
        merged_specs.update(_build_specifications(package, specs_section))
        merged_ns_descs.update(_build_namespace_descriptions(package, traits_section))
        merged_pkg_descs[package] = package_description

    return TraitCatalogue(
        merged_traits,
        merged_specs,
        package_descriptions=merged_pkg_descs,
        namespace_descriptions=merged_ns_descs,
    )


def _load_default_yaml() -> dict[str, Any]:
    """Load traits.yml from the openassetio_mediacreation package.

    :returns: Parsed YAML dict.
    """
    traits_path = importlib.resources.files("openassetio_mediacreation") / "traits.yml"
    return yaml.safe_load(traits_path.read_text(encoding="utf-8"))


def _load_env_var_yamls() -> list[dict[str, Any]]:
    """Load parsed YAML dicts from paths in :data:`_ENV_VAR`.

    Each path in the ``os.pathsep``-separated value is read and parsed. Paths that do
    not exist or fail to parse are logged as warnings and skipped.

    :returns: List of parsed YAML dicts, one per successfully loaded file, in the order
        they appear in the env var.
    """
    raw = os.environ.get(_ENV_VAR, "")
    if not raw:
        return []

    yaml_list: list[dict[str, Any]] = []
    for raw_segment in raw.split(os.pathsep):
        stripped = raw_segment.strip()
        if not stripped:
            continue
        path = Path(stripped)
        if not path.is_file():
            _log.warning("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS: skipping non-existent path: %s", path)
            continue
        try:
            yaml_data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            _log.warning("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS: failed to load %s: %s", path, exc)
            continue
        # safe_load returns None for empty files and can return non-dict
        # types (e.g. a list) for valid-but-unexpected YAML.
        if not isinstance(yaml_data, dict):
            _log.warning("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS: %s is not a YAML mapping, skipping", path)
            continue
        yaml_list.append(yaml_data)

    return yaml_list


def _build_namespace_descriptions(package: str, traits_section: dict[str, Any]) -> dict[str, str]:
    """Extract namespace-level descriptions from the traits section.

    :param package: Package name from the YAML root.
    :param traits_section: The ``traits`` dict from the YAML.

    :returns: Mapping of ``"{package}:{namespace}"`` to description string.
    """
    return {f"{package}:{namespace}": ns_data.get("description", "") for namespace, ns_data in traits_section.items()}


def _build_traits(package: str, traits_section: dict[str, Any]) -> dict[str, TraitDefinition]:
    """Parse the ``traits`` section of a traits.yml into definitions.

    :param package: Package name from the YAML root.
    :param traits_section: The ``traits`` dict from the YAML.

    :returns: Mapping of trait ID to :class:`TraitDefinition`.
    """
    definitions: dict[str, TraitDefinition] = {}
    for namespace, ns_data in traits_section.items():
        members = ns_data.get("members", {})
        if not members:
            _log.warning("Package '%s': trait namespace '%s' has no members", package, namespace)
            continue
        for member_name, member_data in members.items():
            versions = member_data.get("versions", {})
            if not versions:
                _log.warning("Package '%s': trait '%s.%s' has no versions", package, namespace, member_name)
                continue
            for version_str, version_data in versions.items():
                trait_id = _make_versioned_id(package, namespace, member_name, version_str)

                raw_properties = version_data.get("properties", {})
                properties = {
                    prop_name: TraitProperty(
                        name=prop_name,
                        type=prop_data.get("type", "string"),
                        description=prop_data.get("description", ""),
                    )
                    for prop_name, prop_data in (raw_properties or {}).items()
                }

                definitions[trait_id] = TraitDefinition(
                    trait_id=trait_id,
                    package=package,
                    namespace=namespace,
                    member_name=member_name,
                    description=version_data.get("description", ""),
                    version=version_str,
                    usage=version_data.get("usage", []),
                    properties=properties,
                )
    return definitions


def _build_specifications(package: str, specs_section: dict[str, Any]) -> dict[str, SpecificationDefinition]:
    """Parse the ``specifications`` section of a traits.yml.

    :param package: Package name from the YAML root.
    :param specs_section: The ``specifications`` dict from the YAML.

    :returns: Mapping of spec ID to :class:`SpecificationDefinition`.
    """
    definitions: dict[str, SpecificationDefinition] = {}
    for namespace, ns_data in specs_section.items():
        members = ns_data.get("members", {})
        if not members:
            _log.warning("Package '%s': specification namespace '%s' has no members", package, namespace)
            continue
        for member_name, member_data in members.items():
            versions = member_data.get("versions", {})
            if not versions:
                _log.warning("Package '%s': specification '%s.%s' has no versions", package, namespace, member_name)
                continue
            for version_str, version_data in versions.items():
                # Prefix "specification:" to avoid collisions with trait IDs
                # that share the same namespace and member name.
                spec_id = _make_versioned_id(
                    package,
                    f"specification:{namespace}",
                    member_name,
                    version_str,
                )

                # Each traitSet entry is {namespace, name, version} with an
                # optional "package" key for cross-package references.
                trait_refs = version_data.get("traitSet", [])
                trait_ids = _parse_trait_set(package, namespace, member_name, version_str, trait_refs)

                definitions[spec_id] = SpecificationDefinition(
                    spec_id=spec_id,
                    package=package,
                    namespace=namespace,
                    member_name=member_name,
                    description=version_data.get("description", ""),
                    usage=version_data.get("usage", []),
                    trait_ids=trait_ids,
                )
    return definitions


def _parse_trait_set(
    package: str,
    spec_namespace: str,
    spec_member: str,
    spec_version: str,
    trait_refs: list[Any],
) -> list[str]:
    """Parse a specification's traitSet entries into trait IDs.

    Each entry should be a dict with ``namespace``, ``name``, and ``version`` keys (and
    an optional ``package`` override). Malformed entries (non-dict, missing keys) are
    logged as warnings and skipped rather than aborting the entire catalogue build.

    :param package: Default package name from the specification's YAML root.
    :param spec_namespace: Namespace of the specification (for log context).
    :param spec_member: Member name of the specification (for log context).
    :param spec_version: Version of the specification (for log context).
    :param trait_refs: Raw list of traitSet entries from the YAML.

    :returns: List of fully-qualified trait ID strings.
    """
    spec_label = f"{spec_namespace}.{spec_member} v{spec_version}"
    trait_ids: list[str] = []
    for ref in trait_refs:
        if not isinstance(ref, dict):
            _log.warning(
                "Package '%s': traitSet entry in specification '%s' is not a mapping, skipping: %s",
                package,
                spec_label,
                ref,
            )
            continue
        try:
            trait_ids.append(
                _make_versioned_id(
                    ref.get("package", package),
                    ref["namespace"],
                    ref["name"],
                    ref["version"],
                )
            )
        except KeyError as exc:
            _log.warning(
                "Package '%s': traitSet entry in specification '%s' missing key %s, skipping: %s",
                package,
                spec_label,
                exc,
                ref,
            )
    return trait_ids


def _make_versioned_id(package: str, namespace: str, member_name: str, version_str: str) -> str:
    """Build a versioned ID from its components.

    Version 1 uses ``{package}:{namespace}.{MemberName}``; version 2+ appends
    ``.v{version}``.

    :param package: Package name.
    :param namespace: Namespace within the package.
    :param member_name: Member name within the namespace.
    :param version_str: Version string (e.g. ``"1"``, ``"2"``).

    :returns: The fully-qualified ID string.
    """
    base = f"{package}:{namespace}.{member_name}"
    if version_str == "1":
        return base
    return f"{base}.v{version_str}"
