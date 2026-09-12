#!/usr/bin/env python3
"""Validate and publish the deterministic LineageWeave ontology Pages site.

This safety wrapper keeps the renderer focused on presentation while enforcing
fail-closed graph and filesystem boundaries before the renderer may replace an
output directory or emit links derived from ontology IRIs.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, PROV, RDF, RDFS, SH, SKOS

try:
    from scripts.ontology_site_contract import public_fragment
except ModuleNotFoundError:  # direct execution with ``scripts`` as sys.path[0]
    from ontology_site_contract import public_fragment

OUTPUT_MARKER = ".lineageweave-ontology-site"
SOURCE_RELATIVE_PATH = Path("docs/ontology/lineageweave-kg.ttl")
PROV_PROFILE_RELATIVE_PATH = Path("docs/ontology/prov-o-support-profile.ttl")
COMPATIBILITY_RELATIVE_PATH = Path("docs/ontology/namespace-compatibility.ttl")
SHAPES_RELATIVE_PATH = Path("docs/ontology/lineageweave-kg-shapes.ttl")
#: ADR 0207: the repository-case namespace is canonical and the
#: lowercase form is the deprecated compatibility vocabulary.
CANONICAL_NAMESPACE = "https://contextualwisdomlab.github.io/LineageWeave/ontology#"
DEPRECATED_NAMESPACE = "https://contextualwisdomlab.github.io/lineageweave/ontology#"
STANDARD_SHACL_PATHS = frozenset(
    {
        RDF.subject,
        RDF.predicate,
        RDF.object,
        PROV.wasDerivedFrom,
        PROV.generatedAtTime,
    }
)

_MAPPING_FOR_KIND = {
    OWL.Class: OWL.equivalentClass,
    OWL.ObjectProperty: OWL.equivalentProperty,
    OWL.DatatypeProperty: OWL.equivalentProperty,
    OWL.AnnotationProperty: OWL.equivalentProperty,
    SKOS.Concept: SKOS.exactMatch,
}


def _load_renderer(repository_root: Path) -> ModuleType:
    """Load the sibling deterministic renderer from one repository root."""
    renderer_script_path = repository_root / "scripts" / "build_ontology_site.py"
    renderer_module_spec = importlib.util.spec_from_file_location(
        "lineageweave_ontology_renderer", renderer_script_path
    )
    if renderer_module_spec is None or renderer_module_spec.loader is None:
        raise RuntimeError(
            f"ontology renderer could not be loaded: {renderer_script_path}"
        )
    renderer_module = importlib.util.module_from_spec(renderer_module_spec)
    renderer_module_spec.loader.exec_module(renderer_module)
    return renderer_module


def _ontology_fragment(ontology_resource: URIRef) -> str:
    """Return the local fragment used by the renderer as an HTML identifier."""
    ontology_iri = str(ontology_resource)
    if "#" in ontology_iri:
        return ontology_iri.rsplit("#", 1)[1]
    return ontology_iri.rstrip("/").rsplit("/", 1)[-1]


def _public_ontology_subjects(
    ontology_graph: Graph,
    ontology_renderer: ModuleType,
) -> set[URIRef]:
    """Return URI subjects included in the renderer's public term inventory."""
    return {
        ontology_subject
        for _, term_type in ontology_renderer.TERM_TYPES
        for ontology_subject in ontology_graph.subjects(RDF.type, term_type)
        if isinstance(ontology_subject, URIRef)
    }


def validate_public_graph(
    ontology_graph: Graph,
    ontology_renderer: ModuleType,
) -> None:
    """Reject renderer-visible RDF that cannot be published safely."""
    ontology_subjects = _public_ontology_subjects(ontology_graph, ontology_renderer)
    fragment_owner_by_id: dict[str, URIRef] = {}
    for ontology_subject in sorted(ontology_subjects, key=str):
        public_fragment_id = public_fragment(_ontology_fragment(ontology_subject))
        previous_fragment_owner = fragment_owner_by_id.setdefault(
            public_fragment_id, ontology_subject
        )
        if previous_fragment_owner != ontology_subject:
            raise ValueError(
                f"duplicate ontology fragment {public_fragment_id!r}: "
                f"{previous_fragment_owner} and {ontology_subject}"
            )

    for ontology_subject in ontology_subjects:
        for relation_predicate in (
            RDF.type,
            *(
                relation_field[1]
                for relation_field in ontology_renderer.RELATION_FIELDS
            ),
        ):
            for linked_resource in ontology_graph.objects(
                ontology_subject, relation_predicate
            ):
                if (
                    not isinstance(linked_resource, URIRef)
                    or linked_resource in ontology_subjects
                ):
                    continue
                linked_iri_scheme = urlsplit(str(linked_resource)).scheme.lower()
                if linked_iri_scheme not in {"http", "https"}:
                    raise ValueError(
                        f"unsafe linked IRI scheme {linked_iri_scheme!r} "
                        f"for {linked_resource}"
                    )


def _ontology_term_kind(
    ontology_graph: Graph,
    ontology_subject: URIRef,
) -> URIRef | None:
    """Return one supported RDF term kind, including entailed classes."""
    ontology_term_kinds = {
        ontology_term_kind
        for ontology_term_kind in _MAPPING_FOR_KIND
        if (ontology_subject, RDF.type, ontology_term_kind) in ontology_graph
    }
    if any(ontology_graph.objects(ontology_subject, RDFS.subClassOf)):
        ontology_term_kinds.add(OWL.Class)
    return next(iter(ontology_term_kinds)) if len(ontology_term_kinds) == 1 else None


def validate_compatibility_graph(
    canonical_ontology_graph: Graph,
    compatibility_ontology_graph: Graph,
) -> None:
    """Reject namespace mappings whose local name or RDF term kind differs."""
    namespace_mappings = {
        (canonical_resource, mapping_predicate, deprecated_resource)
        for mapping_predicate in set(_MAPPING_FOR_KIND.values())
        for canonical_resource, deprecated_resource in (
            compatibility_ontology_graph.subject_objects(mapping_predicate)
        )
    }
    if not namespace_mappings:
        raise ValueError("namespace compatibility vocabulary has no mappings")
    for (
        canonical_resource,
        mapping_predicate,
        deprecated_resource,
    ) in namespace_mappings:
        canonical_iri = str(canonical_resource)
        deprecated_iri = str(deprecated_resource)
        if not canonical_iri.startswith(
            CANONICAL_NAMESPACE
        ) or not deprecated_iri.startswith(DEPRECATED_NAMESPACE):
            raise ValueError(
                "namespace compatibility mapping has an unexpected namespace"
            )
        if canonical_iri.removeprefix(
            CANONICAL_NAMESPACE
        ) != deprecated_iri.removeprefix(DEPRECATED_NAMESPACE):
            raise ValueError(
                "namespace compatibility mapping has different local names"
            )
        canonical_term_kind = _ontology_term_kind(
            canonical_ontology_graph, canonical_resource
        )
        deprecated_term_kind = _ontology_term_kind(
            compatibility_ontology_graph, deprecated_resource
        )
        if canonical_term_kind is None or canonical_term_kind != deprecated_term_kind:
            raise ValueError("namespace compatibility mapping has different term kinds")
        if _MAPPING_FOR_KIND[canonical_term_kind] != mapping_predicate:
            raise ValueError("namespace compatibility mapping uses the wrong predicate")


def validate_shapes_graph(
    shacl_shapes_graph: Graph,
    canonical_ontology_graph: Graph,
) -> None:
    """Reject SHACL shapes whose targets dangle outside the ontology.

    A shape that targets a class absent from the canonical graph, or
    constrains a path neither declared there nor an allowlisted RDF
    reification/PROV-O provenance predicate, would silently validate nothing
    -- the publication boundary refuses it instead (ADR 0207 decision 10).
    Only URI-valued targets and paths are checked; literal sh:path values
    are not part of this contract.
    """
    if not any(shacl_shapes_graph.triples((None, RDF.type, SH.NodeShape))):
        raise ValueError("SHACL shapes graph declares no sh:NodeShape")
    for shacl_predicate in (SH.targetClass, SH.path):
        for linked_resource in shacl_shapes_graph.objects(None, shacl_predicate):
            if (
                not isinstance(linked_resource, URIRef)
                or str(linked_resource).startswith(CANONICAL_NAMESPACE)
                or (
                    shacl_predicate == SH.path
                    and linked_resource in STANDARD_SHACL_PATHS
                )
            ):
                continue
            resource_kind = (
                "targetClass" if shacl_predicate == SH.targetClass else "path"
            )
            raise ValueError(
                f"SHACL {resource_kind} target outside the canonical namespace: "
                f"{linked_resource}"
            )
    declared_ontology_classes = {
        ontology_subject
        for ontology_subject in canonical_ontology_graph.subjects(RDF.type, OWL.Class)
        if isinstance(ontology_subject, URIRef)
    }
    # Entailed classes: anything with a subclass assertion is a class.
    declared_ontology_classes.update(
        ontology_subject
        for ontology_subject, _ in canonical_ontology_graph.subject_objects(
            RDFS.subClassOf
        )
        if isinstance(ontology_subject, URIRef)
    )
    declared_ontology_properties = {
        ontology_subject
        for ontology_subject in canonical_ontology_graph.subjects(
            RDF.type, OWL.ObjectProperty
        )
        if isinstance(ontology_subject, URIRef)
    }
    declared_ontology_properties.update(
        ontology_subject
        for ontology_subject in canonical_ontology_graph.subjects(
            RDF.type, OWL.DatatypeProperty
        )
        if isinstance(ontology_subject, URIRef)
    )
    declared_ontology_properties.update(STANDARD_SHACL_PATHS)
    for target_class in shacl_shapes_graph.objects(None, SH.targetClass):
        if target_class not in declared_ontology_classes:
            raise ValueError(
                f"SHACL targetClass is not an ontology class: {target_class}"
            )
    for property_path in shacl_shapes_graph.objects(None, SH.path):
        if property_path not in declared_ontology_properties:
            raise ValueError(
                f"SHACL property path is not an ontology property: {property_path}"
            )


def _validate_output_directory(
    publication_output_dir: Path,
    ontology_source_path: Path,
    prov_profile_path: Path,
) -> Path:
    """Resolve an output path and ensure replacement cannot delete source data."""
    requested_output_path = publication_output_dir.expanduser()
    if requested_output_path.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    resolved_output_path = requested_output_path.resolve()
    if ontology_source_path.is_relative_to(
        resolved_output_path
    ) or prov_profile_path.is_relative_to(resolved_output_path):
        raise ValueError("output directory overlaps ontology source files")
    if (
        resolved_output_path.exists()
        and not (resolved_output_path / OUTPUT_MARKER).is_file()
    ):
        raise ValueError("refusing to replace an unmarked output directory")
    return resolved_output_path


def publish_site(repository_root: Path, publication_output_dir: Path) -> None:
    """Validate sources and publish one safely replaceable static site tree."""
    resolved_repository_root = repository_root.resolve()
    ontology_source_path = resolved_repository_root / SOURCE_RELATIVE_PATH
    prov_profile_path = resolved_repository_root / PROV_PROFILE_RELATIVE_PATH
    compatibility_source_path = resolved_repository_root / COMPATIBILITY_RELATIVE_PATH
    shapes_source_path = resolved_repository_root / SHAPES_RELATIVE_PATH
    if not ontology_source_path.is_file():
        raise FileNotFoundError(f"ontology source is missing: {ontology_source_path}")
    if not prov_profile_path.is_file():
        raise FileNotFoundError(
            f"PROV-O support profile is missing: {prov_profile_path}"
        )
    if not compatibility_source_path.is_file():
        raise FileNotFoundError(
            "namespace compatibility vocabulary is missing: "
            f"{compatibility_source_path}"
        )
    if not shapes_source_path.is_file():
        raise FileNotFoundError(f"SHACL shapes graph is missing: {shapes_source_path}")

    resolved_output_dir = _validate_output_directory(
        publication_output_dir, ontology_source_path, prov_profile_path
    )
    ontology_renderer = _load_renderer(resolved_repository_root)
    canonical_ontology_graph = Graph().parse(ontology_source_path, format="turtle")
    Graph().parse(prov_profile_path, format="turtle")
    compatibility_ontology_graph = Graph().parse(
        compatibility_source_path, format="turtle"
    )
    shacl_shapes_graph = Graph().parse(shapes_source_path, format="turtle")
    validate_public_graph(canonical_ontology_graph, ontology_renderer)
    validate_compatibility_graph(canonical_ontology_graph, compatibility_ontology_graph)
    validate_shapes_graph(shacl_shapes_graph, canonical_ontology_graph)

    if resolved_output_dir.exists():
        shutil.rmtree(resolved_output_dir)
    try:
        ontology_renderer.build_site(resolved_repository_root, resolved_output_dir)
    except BaseException:
        shutil.rmtree(resolved_output_dir, ignore_errors=True)
        raise
    (resolved_output_dir / OUTPUT_MARKER).write_text("", encoding="utf-8")


def _parse_publication_arguments(
    command_line_arguments: Iterable[str] | None = None,
) -> argparse.Namespace:
    """Parse repository and output paths for the publication command."""
    ontology_publication_parser = argparse.ArgumentParser(description=__doc__)
    ontology_publication_parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="LineageWeave repository root",
    )
    ontology_publication_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_site"),
        help="Static site output directory",
    )
    return ontology_publication_parser.parse_args(command_line_arguments)


def main(command_line_arguments: Iterable[str] | None = None) -> int:
    """Publish the site from CLI arguments and return a process exit code."""
    command_arguments = _parse_publication_arguments(command_line_arguments)
    publish_site(command_arguments.repository_root, command_arguments.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
