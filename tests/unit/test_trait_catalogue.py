# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Tests for the trait catalogue module."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import griptape_nodes_library_openassetio.trait_catalogue as catalogue_mod
import pytest
import yaml
from griptape_nodes_library_openassetio.trait_catalogue import (
    TraitCatalogue,
    TraitDefinition,
    TraitProperty,
    build_catalogue_from_yaml_list,
    load_default_catalogue,
)

_RESOURCES = Path(__file__).parent.parent / "resources"


@pytest.fixture
def test_yaml_data() -> dict:
    """Load the test traits YAML as a dict."""
    return yaml.safe_load((_RESOURCES / "test_traits.yml").read_text())


@pytest.fixture
def catalogue(test_yaml_data: dict) -> TraitCatalogue:
    """Build a catalogue from the test traits YAML."""
    return build_catalogue_from_yaml_list([test_yaml_data])


class TestTraitProperty:
    """Tests for the TraitProperty dataclass."""

    def test_frozen(self) -> None:
        prop = TraitProperty(name="location", type="string", description="The location")
        with pytest.raises(AttributeError):
            prop.name = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        prop = TraitProperty(name="location", type="string", description="The location")
        assert prop.name == "location"
        assert prop.type == "string"
        assert prop.description == "The location"


class TestTraitDefinition:
    """Tests for the TraitDefinition dataclass."""

    def test_frozen(self) -> None:
        defn = TraitDefinition(
            trait_id="pkg:ns.Member",
            package="pkg",
            namespace="ns",
            member_name="Member",
            version="1",
            description="desc",
            usage=["entity"],
            properties={},
        )
        with pytest.raises(AttributeError):
            defn.trait_id = "other"  # type: ignore[misc]


class TestPackageAndNamespaceDescriptions:
    """Tests for package and namespace descriptions in the catalogue."""

    def test_package_description_stored(self, catalogue: TraitCatalogue) -> None:
        """Catalogue should store the root-level YAML description keyed by package."""
        assert catalogue.get_package_description("test-traits") == "Test trait definitions"

    def test_namespace_description_stored(self, catalogue: TraitCatalogue) -> None:
        """Catalogue should index namespace descriptions by qualified name."""
        assert catalogue.get_namespace_description("test-traits:content") == "Test content traits"
        assert catalogue.get_namespace_description("test-traits:identity") == "Test identity traits"

    def test_namespace_description_returns_empty_for_unknown(self, catalogue: TraitCatalogue) -> None:
        """Unknown namespace should return an empty string, not raise."""
        assert catalogue.get_namespace_description("no-such:namespace") == ""  # noqa: PLC1901

    def test_package_description_defaults_to_empty(self) -> None:
        """Missing description key in YAML should default to empty string."""
        yaml_data = _make_minimal_yaml("empty", "ns", "T", "string")
        del yaml_data["description"]
        cat = build_catalogue_from_yaml_list([yaml_data])
        assert cat.get_package_description("empty") == ""  # noqa: PLC1901

    def test_package_description_unknown_package_returns_empty(self) -> None:
        """Unknown package name should return an empty string, not raise."""
        yaml_data = _make_minimal_yaml("known", "ns", "T", "string")
        yaml_data["description"] = "Known desc"
        cat = build_catalogue_from_yaml_list([yaml_data])
        assert cat.get_package_description("no-such-package") == ""  # noqa: PLC1901


class TestTraitAndSpecParsing:
    """Tests for trait and specification parsing from a single YAML source."""

    def test_version_1_trait_id(self, catalogue: TraitCatalogue) -> None:
        """Version 1 traits use {package}:{namespace}.{MemberName} format."""
        defn = catalogue.get_trait("test-traits:content.LocatableContent")
        assert defn is not None
        assert defn.trait_id == "test-traits:content.LocatableContent"
        assert defn.package == "test-traits"
        assert defn.namespace == "content"
        assert defn.member_name == "LocatableContent"

    def test_version_2_trait_id(self, catalogue: TraitCatalogue) -> None:
        """Version 2+ traits append .v{version} to the trait ID."""
        defn = catalogue.get_trait("test-traits:versioned.Multi.v2")
        assert defn is not None
        assert defn.trait_id == "test-traits:versioned.Multi.v2"

    def test_properties_extracted(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:content.LocatableContent")
        assert defn is not None
        assert "location" in defn.properties
        assert "mimeType" in defn.properties
        assert defn.properties["location"].type == "string"
        assert defn.properties["mimeType"].type == "string"

    def test_trait_with_no_properties(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:identity.NoProps")
        assert defn is not None
        assert defn.properties == {}

    def test_description_captured(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:content.LocatableContent")
        assert defn is not None
        assert defn.description == "Test locatable content"

    def test_version_captured(self, catalogue: TraitCatalogue) -> None:
        v1 = catalogue.get_trait("test-traits:content.LocatableContent")
        assert v1 is not None
        assert v1.version == "1"

        v2 = catalogue.get_trait("test-traits:versioned.Multi.v2")
        assert v2 is not None
        assert v2.version == "2"

    def test_integer_property_type(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:versioned.Multi")
        assert defn is not None
        assert defn.properties["alpha"].type == "integer"

    def test_float_property_type(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:versioned.Multi.v2")
        assert defn is not None
        assert defn.properties["beta"].type == "float"

    def test_unknown_trait_returns_none(self, catalogue: TraitCatalogue) -> None:
        assert catalogue.get_trait("no-such:trait.Id") is None

    def test_all_trait_ids_returns_sorted_list(self, catalogue: TraitCatalogue) -> None:
        ids = catalogue.resolvable_trait_ids()
        assert ids == sorted(ids)
        # Excluded: identity.NoProps (no properties), usage.Entity (no properties),
        # managementPolicy.Managed (non-entity usage). Remaining: 4.
        assert len(ids) == 4
        assert "test-traits:identity.NoProps" not in ids
        assert "test-traits:usage.Entity" not in ids

    def test_all_trait_ids_excludes_propertyless_traits(self, catalogue: TraitCatalogue) -> None:
        """Traits with no properties are not useful for resolve and should be excluded."""
        ids = catalogue.resolvable_trait_ids()
        assert "test-traits:identity.NoProps" not in ids
        assert "test-traits:content.LocatableContent" in ids

    def test_all_trait_ids_excludes_non_entity_traits(self, catalogue: TraitCatalogue) -> None:
        """Traits whose usage does not include 'entity' should be excluded."""
        ids = catalogue.resolvable_trait_ids()
        assert "test-traits:managementPolicy.Managed" not in ids

    def test_usage_stored_on_trait(self, catalogue: TraitCatalogue) -> None:
        defn = catalogue.get_trait("test-traits:content.LocatableContent")
        assert defn is not None
        assert defn.usage == ["entity"]


class TestBuildCatalogueValidationWarnings:
    """Tests for warning logs when traits YAML has structural issues."""

    def test_trait_namespace_with_no_members_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """A trait namespace with no 'members' key logs a warning."""
        yaml_data = {
            "package": "pkg",
            "traits": {"empty_ns": {"description": "An empty namespace"}},
        }

        with caplog.at_level(logging.WARNING):
            build_catalogue_from_yaml_list([yaml_data])

        assert "empty_ns" in caplog.text
        assert "members" in caplog.text.lower()

    def test_trait_member_with_no_versions_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """A trait member with no 'versions' key logs a warning."""
        yaml_data = {
            "package": "pkg",
            "traits": {
                "ns": {
                    "description": "A namespace",
                    "members": {"Orphan": {"description": "No versions"}},
                },
            },
        }

        with caplog.at_level(logging.WARNING):
            build_catalogue_from_yaml_list([yaml_data])

        assert "Orphan" in caplog.text
        assert "versions" in caplog.text.lower()

    def test_spec_namespace_with_no_members_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """A specification namespace with no 'members' key logs a warning."""
        yaml_data = {
            "package": "pkg",
            "traits": {
                "ns": {
                    "description": "ns",
                    "members": {
                        "T": {
                            "versions": {
                                "1": {
                                    "description": "t",
                                    "usage": ["entity"],
                                    "properties": {"v": {"type": "string", "description": "v"}},
                                }
                            }
                        }
                    },
                }
            },
            "specifications": {"empty_ns": {"description": "Empty spec namespace"}},
        }

        with caplog.at_level(logging.WARNING):
            build_catalogue_from_yaml_list([yaml_data])

        assert "empty_ns" in caplog.text
        assert "members" in caplog.text.lower()

    def test_spec_member_with_no_versions_warns(self, caplog: pytest.LogCaptureFixture) -> None:
        """A specification member with no 'versions' key logs a warning."""
        yaml_data = {
            "package": "pkg",
            "traits": {
                "ns": {
                    "description": "ns",
                    "members": {
                        "T": {
                            "versions": {
                                "1": {
                                    "description": "t",
                                    "usage": ["entity"],
                                    "properties": {"v": {"type": "string", "description": "v"}},
                                }
                            }
                        }
                    },
                }
            },
            "specifications": {
                "ns": {
                    "description": "A namespace",
                    "members": {"OrphanSpec": {"description": "No versions"}},
                },
            },
        }

        with caplog.at_level(logging.WARNING):
            build_catalogue_from_yaml_list([yaml_data])

        assert "OrphanSpec" in caplog.text
        assert "versions" in caplog.text.lower()

    def test_traits_section_non_dict_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A 'traits' value that is not a dict should be skipped with a warning."""
        yaml_data = {
            "package": "pkg",
            "traits": ["not", "a", "dict"],
            "specifications": {},
        }

        with caplog.at_level(logging.WARNING):
            cat = build_catalogue_from_yaml_list([yaml_data])

        assert cat.resolvable_trait_ids() == []
        assert "not a mapping" in caplog.text.lower()

    def test_specifications_section_non_dict_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A 'specifications' value that is not a dict should be skipped with a warning."""
        yaml_data = _make_minimal_yaml("pkg", "ns", "T", "string")
        yaml_data["specifications"] = "not a dict"

        with caplog.at_level(logging.WARNING):
            cat = build_catalogue_from_yaml_list([yaml_data])

        # Traits should still be parsed.
        assert cat.get_trait("pkg:ns.T") is not None
        assert "not a mapping" in caplog.text.lower()

    def test_malformed_trait_set_entry_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A traitSet entry missing required keys is skipped with a warning."""
        yaml_data = _make_minimal_yaml("pkg", "ns", "T", "string")
        yaml_data["specifications"] = {
            "ns": {
                "description": "ns",
                "members": {
                    "BadSpec": {
                        "versions": {
                            "1": {
                                "description": "spec",
                                "usage": ["entity"],
                                "traitSet": [
                                    {"namespace": "ns", "name": "T", "version": "1"},
                                    {"bad": "entry"},
                                ],
                            },
                        },
                    },
                },
            },
        }

        with caplog.at_level(logging.WARNING):
            cat = build_catalogue_from_yaml_list([yaml_data])

        spec = cat.get_specification("pkg:specification:ns.BadSpec")
        assert spec is not None
        # The valid trait ref should still be included.
        assert "pkg:ns.T" in spec.trait_ids
        # The malformed entry should have been skipped.
        assert len(spec.trait_ids) == 1
        assert "traitSet" in caplog.text

    def test_non_dict_trait_set_entry_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A traitSet entry that is a string instead of a dict is skipped."""
        yaml_data = _make_minimal_yaml("pkg", "ns", "T", "string")
        yaml_data["specifications"] = {
            "ns": {
                "description": "ns",
                "members": {
                    "StrSpec": {
                        "versions": {
                            "1": {
                                "description": "spec",
                                "usage": ["entity"],
                                "traitSet": ["just_a_string"],
                            },
                        },
                    },
                },
            },
        }

        with caplog.at_level(logging.WARNING):
            cat = build_catalogue_from_yaml_list([yaml_data])

        spec = cat.get_specification("pkg:specification:ns.StrSpec")
        assert spec is not None
        assert spec.trait_ids == []
        assert "traitSet" in caplog.text


class TestSpecifications:
    """Tests for specification parsing and lookup."""

    def test_specification_parsed(self, catalogue: TraitCatalogue) -> None:
        spec = catalogue.get_specification("test-traits:specification:content.NamedContent")
        assert spec is not None
        assert spec.spec_id == "test-traits:specification:content.NamedContent"
        assert spec.package == "test-traits"
        assert spec.namespace == "content"
        assert spec.member_name == "NamedContent"

    def test_specification_trait_ids(self, catalogue: TraitCatalogue) -> None:
        """A specification should list its constituent trait IDs."""
        spec = catalogue.get_specification("test-traits:specification:content.NamedContent")
        assert spec is not None
        assert spec.trait_ids == [
            "test-traits:usage.Entity",
            "test-traits:content.LocatableContent",
            "test-traits:identity.DisplayName",
        ]

    def test_cross_package_trait_references(self, catalogue: TraitCatalogue) -> None:
        """Trait refs with an explicit 'package' key use that package, not the spec's."""
        spec = catalogue.get_specification("test-traits:specification:content.CrossPackageSpec")
        assert spec is not None
        assert spec.trait_ids == [
            # Local trait — package defaults to the spec's package.
            "test-traits:content.LocatableContent",
            # External trait — package comes from the traitSet entry.
            "external-pkg:ext.SomeTrait",
        ]

    def test_unknown_specification_returns_none(self, catalogue: TraitCatalogue) -> None:
        assert catalogue.get_specification("no-such:spec.Id") is None


class TestAllChoosableIds:
    """Tests for all_choosable_ids() which merges traits and specifications."""

    def test_includes_traits_with_properties(self, catalogue: TraitCatalogue) -> None:
        ids = catalogue.all_choosable_ids()
        assert "test-traits:content.LocatableContent" in ids

    def test_includes_specifications_with_propertied_traits(self, catalogue: TraitCatalogue) -> None:
        ids = catalogue.all_choosable_ids()
        assert "test-traits:specification:content.NamedContent" in ids

    def test_excludes_specifications_whose_traits_all_lack_properties(self, catalogue: TraitCatalogue) -> None:
        """PropslessSpec only references traits with no properties, so it should be excluded."""
        ids = catalogue.all_choosable_ids()
        assert "test-traits:specification:content.PropslessSpec" not in ids

    def test_excludes_propertyless_traits(self, catalogue: TraitCatalogue) -> None:
        ids = catalogue.all_choosable_ids()
        assert "test-traits:identity.NoProps" not in ids

    def test_excludes_non_entity_traits(self, catalogue: TraitCatalogue) -> None:
        """Traits whose usage does not include 'entity' should not be choosable."""
        ids = catalogue.all_choosable_ids()
        assert "test-traits:managementPolicy.Managed" not in ids

    def test_excludes_non_entity_specifications(self, catalogue: TraitCatalogue) -> None:
        """Specifications whose usage does not include 'entity' should not be choosable."""
        ids = catalogue.all_choosable_ids()
        assert "test-traits:specification:lifecycle.VersionsRelationship" not in ids

    def test_specifications_before_traits(self, catalogue: TraitCatalogue) -> None:
        """Specifications should appear before traits, both groups sorted internally."""
        ids = catalogue.all_choosable_ids()
        # NamedContent is a spec, LocatableContent is a trait.
        spec_idx = ids.index("test-traits:specification:content.NamedContent")
        trait_idx = ids.index("test-traits:content.LocatableContent")
        assert spec_idx < trait_idx


class TestExpandToTraitIds:
    """Tests for expand_to_trait_ids() which expands specifications to their traits."""

    def test_trait_ids_pass_through(self, catalogue: TraitCatalogue) -> None:
        """Plain trait IDs are returned as-is."""
        result = catalogue.expand_to_resolvable_trait_ids(["test-traits:content.LocatableContent"])
        assert result == ["test-traits:content.LocatableContent"]

    def test_specification_expands_to_trait_ids(self, catalogue: TraitCatalogue) -> None:
        """Specs expand to their constituent traits that have properties."""
        result = catalogue.expand_to_resolvable_trait_ids(["test-traits:specification:content.NamedContent"])
        assert "test-traits:content.LocatableContent" in result
        assert "test-traits:identity.DisplayName" in result

    def test_specification_excludes_propertyless_traits(self, catalogue: TraitCatalogue) -> None:
        """Propertyless traits from a specification are filtered out."""
        result = catalogue.expand_to_resolvable_trait_ids(["test-traits:specification:content.NamedContent"])
        assert "test-traits:usage.Entity" not in result

    def test_deduplicates(self, catalogue: TraitCatalogue) -> None:
        """If a trait appears both directly and via a spec, it should appear only once."""
        result = catalogue.expand_to_resolvable_trait_ids(
            [
                "test-traits:content.LocatableContent",
                "test-traits:specification:content.NamedContent",
            ]
        )
        count = result.count("test-traits:content.LocatableContent")
        assert count == 1

    def test_preserves_order_traits_first(self, catalogue: TraitCatalogue) -> None:
        """Directly selected traits should appear before spec-expanded ones."""
        result = catalogue.expand_to_resolvable_trait_ids(
            [
                "test-traits:identity.DisplayName",
                "test-traits:specification:content.NamedContent",
            ]
        )
        # DisplayName was selected directly, so it comes first.
        # The spec then adds LocatableContent (DisplayName already seen, Entity filtered).
        assert result[0] == "test-traits:identity.DisplayName"

    def test_unknown_ids_filtered_out(self, catalogue: TraitCatalogue) -> None:
        """IDs not in the catalogue are filtered out (not in valid trait set)."""
        result = catalogue.expand_to_resolvable_trait_ids(["custom:ns.Trait"])
        assert result == []

    def test_non_entity_trait_filtered_out(self, catalogue: TraitCatalogue) -> None:
        """Traits without 'entity' usage are excluded even when selected directly."""
        result = catalogue.expand_to_resolvable_trait_ids(["test-traits:managementPolicy.Managed"])
        assert result == []

    def test_empty_input(self, catalogue: TraitCatalogue) -> None:
        assert catalogue.expand_to_resolvable_trait_ids([]) == []


class TestLoadDefaultCatalogue:
    """Tests for the load_default_catalogue() function."""

    def test_returns_catalogue_instance(self) -> None:
        cat = load_default_catalogue()
        assert isinstance(cat, TraitCatalogue)

    def test_returns_fresh_instance_each_call(self) -> None:
        """load_default_catalogue() builds a new catalogue each time."""
        a = load_default_catalogue()
        b = load_default_catalogue()
        assert a is not b

    def test_contains_mediacreation_traits(self) -> None:
        """The default catalogue contains traits from openassetio-mediacreation."""
        cat = load_default_catalogue()
        # LocatableContent is a well-known trait that should always be present
        assert cat.get_trait("openassetio-mediacreation:content.LocatableContent") is not None


class TestBuildCatalogueFromYamlList:
    """Tests for build_catalogue_from_yaml_list()."""

    def test_empty_list_returns_empty_catalogue(self) -> None:
        """Building from zero YAML dicts produces an empty catalogue."""
        result = build_catalogue_from_yaml_list([])
        assert result.resolvable_trait_ids() == []

    def test_traits_from_both_yamls(self) -> None:
        """Traits from two YAML sources are both present in the catalogue."""
        yaml_a = _make_minimal_yaml("pkg-a", "ns", "TraitA", "string")
        yaml_b = _make_minimal_yaml("pkg-b", "ns", "TraitB", "integer")

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        assert result.get_trait("pkg-a:ns.TraitA") is not None
        assert result.get_trait("pkg-b:ns.TraitB") is not None

    def test_later_yaml_overwrites_traits(self) -> None:
        """When two YAML sources define the same trait ID, the later one wins."""
        yaml_a = _make_minimal_yaml("pkg", "ns", "Thing", "string", description="Original")
        yaml_b = _make_minimal_yaml("pkg", "ns", "Thing", "integer", description="Override")

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        defn = result.get_trait("pkg:ns.Thing")
        assert defn is not None
        assert defn.description == "Override"
        assert defn.properties["value"].type == "integer"

    def test_specifications_merged(self) -> None:
        """Specifications from multiple YAML sources are merged."""
        yaml_a = _make_yaml_with_spec("pkg-a", "ns", "SpecA")
        yaml_b = _make_yaml_with_spec("pkg-b", "ns", "SpecB")

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        assert result.get_specification("pkg-a:specification:ns.SpecA") is not None
        assert result.get_specification("pkg-b:specification:ns.SpecB") is not None

    def test_package_descriptions_merged(self) -> None:
        """Package descriptions from multiple YAML sources are merged."""
        yaml_a = _make_minimal_yaml("pkg-a", "ns", "T", "string")
        yaml_a["description"] = "Package A"
        yaml_b = _make_minimal_yaml("pkg-b", "ns", "T", "string")
        yaml_b["description"] = "Package B"

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        assert result.get_package_description("pkg-a") == "Package A"
        assert result.get_package_description("pkg-b") == "Package B"

    def test_namespace_descriptions_merged(self) -> None:
        """Namespace descriptions from multiple YAML sources are merged."""
        yaml_a = _make_minimal_yaml("pkg-a", "ns", "T", "string")
        yaml_b = _make_minimal_yaml("pkg-b", "ns", "T", "string")

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        assert result.get_namespace_description("pkg-a:ns")
        assert result.get_namespace_description("pkg-b:ns")

    def test_later_package_description_overwrites(self) -> None:
        """Later YAML source's package description overwrites earlier one."""
        yaml_a = _make_minimal_yaml("pkg", "ns", "T", "string")
        yaml_a["description"] = "Original"
        yaml_b = _make_minimal_yaml("pkg", "ns", "T", "string")
        yaml_b["description"] = "Overwritten"

        result = build_catalogue_from_yaml_list([yaml_a, yaml_b])

        assert result.get_package_description("pkg") == "Overwritten"

    def test_missing_package_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A YAML dict without a ``package`` key is skipped and a warning is logged."""
        good = _make_minimal_yaml("good-pkg", "ns", "Trait", "string")
        bad = {"traits": {"ns": {"description": "orphan", "members": {}}}}

        with caplog.at_level(logging.WARNING):
            result = build_catalogue_from_yaml_list([bad, good])

        # The bad entry is skipped entirely — its traits do not appear.
        assert result.get_trait("good-pkg:ns.Trait") is not None
        assert not result.get_package_description("")
        assert "package" in caplog.text

    def test_empty_package_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A YAML dict with an empty ``package`` string is skipped and a warning is logged."""
        good = _make_minimal_yaml("good-pkg", "ns", "Trait", "string")
        bad = {"package": "", "traits": {"ns": {"description": "orphan", "members": {}}}}

        with caplog.at_level(logging.WARNING):
            result = build_catalogue_from_yaml_list([bad, good])

        assert result.get_trait("good-pkg:ns.Trait") is not None
        assert not result.get_package_description("")
        assert "package" in caplog.text

    def test_no_traits_and_no_specs_skipped_with_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """A YAML dict with a package but no traits or specs is skipped with a warning."""
        yaml_data = {"package": "empty-pkg", "description": "Nothing here"}

        with caplog.at_level(logging.WARNING):
            result = build_catalogue_from_yaml_list([yaml_data])

        # The entry is skipped — package description is not recorded.
        assert not result.get_package_description("empty-pkg")
        assert "empty-pkg" in caplog.text


class TestLoadEnvVarYamls:
    """Tests for _load_env_var_yamls()."""

    def test_returns_empty_when_env_var_not_set(self) -> None:
        """Returns an empty list when the env var is not set."""
        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001
        assert result == []

    def test_returns_empty_for_empty_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns an empty list when the env var is empty."""
        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", "")
        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001
        assert result == []

    def test_loads_single_yaml_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Loads a single YAML file and returns its parsed dict."""
        yaml_data = _make_minimal_yaml("custom", "ns", "Foo", "string")
        yaml_file = tmp_path / "traits.yml"
        yaml_file.write_text(yaml.dump(yaml_data))

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001

        assert len(result) == 1
        assert result[0]["package"] == "custom"

    def test_skips_nonexistent_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Non-existent paths are skipped with a warning."""
        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(tmp_path / "missing.yml"))
        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001
        assert result == []

    def test_skips_invalid_yaml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Files with invalid YAML are skipped with a warning."""
        bad_file = tmp_path / "bad.yml"
        bad_file.write_text(": : : not valid yaml [[[")

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(bad_file))

        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001
        assert result == []

    def test_skips_empty_segments(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty segments in the path list are skipped."""
        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", f"{os.pathsep}{os.pathsep}")
        result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001
        assert result == []

    def test_skips_empty_yaml_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An empty YAML file (safe_load returns None) is skipped with a warning."""
        empty_file = tmp_path / "empty.yml"
        empty_file.write_text("")

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(empty_file))

        with caplog.at_level(logging.WARNING):
            result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001

        assert result == []
        assert "not a YAML mapping" in caplog.text

    def test_skips_non_dict_yaml(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A YAML file that parses to a list (not a dict) is skipped with a warning."""
        list_file = tmp_path / "list.yml"
        list_file.write_text("- item1\n- item2\n")

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(list_file))

        with caplog.at_level(logging.WARNING):
            result = catalogue_mod._load_env_var_yamls()  # noqa: SLF001

        assert result == []
        assert "not a YAML mapping" in caplog.text


def _make_minimal_yaml(
    package: str,
    namespace: str,
    member: str,
    prop_type: str,
    *,
    description: str = "",
) -> dict:
    """Build a minimal traits YAML dict with one trait having one property.

    :param package: Package name.
    :param namespace: Namespace name.
    :param member: Member (trait) name.
    :param prop_type: Property type (``"string"``, ``"integer"``, etc.).
    :param description: Trait description.

    :returns: A parsed YAML-equivalent dict.
    """
    return {
        "package": package,
        "description": f"{package} description",
        "traits": {
            namespace: {
                "description": f"{namespace} namespace",
                "members": {
                    member: {
                        "versions": {
                            "1": {
                                "description": description or f"{member} trait",
                                "usage": ["entity"],
                                "properties": {
                                    "value": {"type": prop_type, "description": "A value"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def _make_yaml_with_spec(
    package: str,
    namespace: str,
    spec_member: str,
) -> dict:
    """Build a traits YAML dict containing a specification.

    :param package: Package name.
    :param namespace: Namespace for the specification.
    :param spec_member: Specification member name.

    :returns: A parsed YAML-equivalent dict.
    """
    return {
        "package": package,
        "description": f"{package} description",
        "traits": {},
        "specifications": {
            namespace: {
                "description": f"{namespace} specs",
                "members": {
                    spec_member: {
                        "versions": {
                            "1": {
                                "description": f"{spec_member} spec",
                                "usage": ["entity"],
                                "traitSet": [
                                    {"namespace": namespace, "name": spec_member, "version": "1"},
                                ],
                            },
                        },
                    },
                },
            },
        },
    }
