# griptape-nodes-library-openassetio
# Copyright (c) 2026 The Foundry Visionmongers Ltd
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS env var support."""

from __future__ import annotations

import os
import textwrap
from typing import TYPE_CHECKING

from griptape_nodes_library_openassetio.trait_catalogue import (
    TraitCatalogue,
    load_default_catalogue,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class TestTraitDefinitionsEnvVar:
    """Tests for the OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS environment variable."""

    def test_custom_traits_appear_in_catalogue(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Traits from a YAML file in the env var are available in the default catalogue."""
        yaml_file = tmp_path / "studio_traits.yml"
        yaml_file.write_text(
            textwrap.dedent("""\
                package: studio-traits
                description: Studio-specific traits
                traits:
                  pipeline:
                    description: Pipeline traits
                    members:
                      TaskStatus:
                        versions:
                          "1":
                            description: Pipeline task status
                            usage:
                              - entity
                            properties:
                              status:
                                type: string
                                description: The task status
                              assignee:
                                type: string
                                description: The assigned artist
            """)
        )

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        catalogue = load_default_catalogue()

        # Custom trait should be present.
        defn = catalogue.get_trait("studio-traits:pipeline.TaskStatus")
        assert defn is not None
        assert defn.package == "studio-traits"
        assert defn.description == "Pipeline task status"
        assert "status" in defn.properties
        assert "assignee" in defn.properties

    def test_custom_traits_coexist_with_mediacreation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Custom traits are merged alongside the built-in openassetio-mediacreation traits."""
        yaml_file = tmp_path / "extra.yml"
        yaml_file.write_text(
            textwrap.dedent("""\
                package: extra
                description: Extra traits
                traits:
                  custom:
                    description: Custom namespace
                    members:
                      Tag:
                        versions:
                          "1":
                            description: A tag trait
                            usage:
                              - entity
                            properties:
                              label:
                                type: string
                                description: The label
            """)
        )

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        catalogue = load_default_catalogue()

        # Built-in mediacreation traits should still be present.
        assert catalogue.get_trait("openassetio-mediacreation:content.LocatableContent") is not None
        # Custom trait should also be present.
        assert catalogue.get_trait("extra:custom.Tag") is not None

    def test_multiple_paths_separated_by_os_pathsep(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Multiple YAML paths separated by os.pathsep are all loaded."""
        file_a = tmp_path / "a.yml"
        file_a.write_text(
            textwrap.dedent("""\
                package: pkg-a
                description: Package A
                traits:
                  ns:
                    description: Namespace A
                    members:
                      TraitA:
                        versions:
                          "1":
                            description: Trait A
                            usage:
                              - entity
                            properties:
                              alpha:
                                type: string
                                description: Alpha property
            """)
        )

        file_b = tmp_path / "b.yml"
        file_b.write_text(
            textwrap.dedent("""\
                package: pkg-b
                description: Package B
                traits:
                  ns:
                    description: Namespace B
                    members:
                      TraitB:
                        versions:
                          "1":
                            description: Trait B
                            usage:
                              - entity
                            properties:
                              beta:
                                type: integer
                                description: Beta property
            """)
        )

        monkeypatch.setenv(
            "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS",
            f"{file_a}{os.pathsep}{file_b}",
        )

        catalogue = load_default_catalogue()

        assert catalogue.get_trait("pkg-a:ns.TraitA") is not None
        assert catalogue.get_trait("pkg-b:ns.TraitB") is not None

    def test_later_file_overwrites_earlier_package(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """When two YAML files define the same package, the later file's traits win."""
        file_a = tmp_path / "a.yml"
        file_a.write_text(
            textwrap.dedent("""\
                package: shared
                description: Original description
                traits:
                  ns:
                    description: Original namespace
                    members:
                      Thing:
                        versions:
                          "1":
                            description: Original trait
                            usage:
                              - entity
                            properties:
                              value:
                                type: string
                                description: Original value
            """)
        )

        file_b = tmp_path / "b.yml"
        file_b.write_text(
            textwrap.dedent("""\
                package: shared
                description: Overwritten description
                traits:
                  ns:
                    description: Overwritten namespace
                    members:
                      Thing:
                        versions:
                          "1":
                            description: Overwritten trait
                            usage:
                              - entity
                            properties:
                              value:
                                type: integer
                                description: Overwritten value
            """)
        )

        monkeypatch.setenv(
            "OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS",
            f"{file_a}{os.pathsep}{file_b}",
        )

        catalogue = load_default_catalogue()

        defn = catalogue.get_trait("shared:ns.Thing")
        assert defn is not None
        assert defn.description == "Overwritten trait"
        assert defn.properties["value"].type == "integer"

    def test_custom_package_overwrites_mediacreation(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A user YAML file with ``package: openassetio-mediacreation`` overrides the built-in."""
        yaml_file = tmp_path / "override.yml"
        yaml_file.write_text(
            textwrap.dedent("""\
                package: openassetio-mediacreation
                description: Overridden mediacreation
                traits:
                  content:
                    description: Custom content
                    members:
                      LocatableContent:
                        versions:
                          "1":
                            description: Customised locatable content
                            usage:
                              - entity
                            properties:
                              location:
                                type: string
                                description: Custom location description
            """)
        )

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        catalogue = load_default_catalogue()

        defn = catalogue.get_trait("openassetio-mediacreation:content.LocatableContent")
        assert defn is not None
        assert defn.description == "Customised locatable content"
        assert defn.properties["location"].description == "Custom location description"

    def test_env_var_not_set_returns_standard_catalogue(self) -> None:
        """When the env var is not set, only the mediacreation catalogue is loaded."""
        catalogue = load_default_catalogue()

        assert isinstance(catalogue, TraitCatalogue)
        assert catalogue.get_trait("openassetio-mediacreation:content.LocatableContent") is not None

    def test_custom_specifications_appear_in_catalogue(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Specifications from custom YAML are available in the merged catalogue."""
        yaml_file = tmp_path / "specs.yml"
        yaml_file.write_text(
            textwrap.dedent("""\
                package: studio-traits
                description: Studio specs
                traits:
                  pipeline:
                    description: Pipeline traits
                    members:
                      Shot:
                        versions:
                          "1":
                            description: A shot
                            usage:
                              - entity
                            properties:
                              name:
                                type: string
                                description: Shot name
                specifications:
                  pipeline:
                    description: Pipeline specs
                    members:
                      ShotSpec:
                        versions:
                          "1":
                            description: A shot specification
                            usage:
                              - entity
                            traitSet:
                              - namespace: pipeline
                                name: Shot
                                version: "1"
            """)
        )

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        catalogue = load_default_catalogue()

        spec = catalogue.get_specification("studio-traits:specification:pipeline.ShotSpec")
        assert spec is not None
        assert spec.trait_ids == ["studio-traits:pipeline.Shot"]

    def test_package_and_namespace_descriptions_merged(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Package and namespace descriptions from custom YAML are accessible."""
        yaml_file = tmp_path / "descs.yml"
        yaml_file.write_text(
            textwrap.dedent("""\
                package: studio-traits
                description: Studio-specific trait definitions
                traits:
                  pipeline:
                    description: Pipeline namespace description
                    members:
                      Dummy:
                        versions:
                          "1":
                            description: A dummy trait
                            usage:
                              - entity
                            properties:
                              x:
                                type: string
                                description: X
            """)
        )

        monkeypatch.setenv("OPENASSETIO_GRIPTAPE_TRAIT_DEFINITIONS", str(yaml_file))

        catalogue = load_default_catalogue()

        assert catalogue.get_package_description("studio-traits") == "Studio-specific trait definitions"
        assert catalogue.get_namespace_description("studio-traits:pipeline") == "Pipeline namespace description"
        # Built-in descriptions should also be present.
        assert catalogue.get_package_description("openassetio-mediacreation")
