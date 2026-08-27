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
    script = repository_root / "scripts" / "build_ontology_site.py"
    spec = importlib.util.spec_from_file_location("lineageweave_ontology_renderer", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"ontology renderer could not be loaded: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fragment(value: URIRef) -> str:
    """Return the local fragment used by the renderer as an HTML identifier."""
    iri = str(value)
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


def _public_subjects(graph: Graph, renderer: ModuleType) -> set[URIRef]:
    """Return URI subjects included in the renderer's public term inventory."""
    return {
        subject
        for _, term_type in renderer.TERM_TYPES
        for subject in graph.subjects(RDF.type, term_type)
        if isinstance(subject, URIRef)
    }


def validate_public_graph(graph: Graph, renderer: ModuleType) -> None:
    """Reject renderer-visible RDF that cannot be published safely."""
    subjects = _public_subjects(graph, renderer)
    fragment_owner: dict[str, URIRef] = {}
    for subject in sorted(subjects, key=str):
        fragment = public_fragment(_fragment(subject))
        owner = fragment_owner.setdefault(fragment, subject)
        if owner != subject:
            raise ValueError(
                f"duplicate ontology fragment {fragment!r}: {owner} and {subject}"
            )

    for subject in subjects:
        for predicate in (RDF.type, *(item[1] for item in renderer.RELATION_FIELDS)):
            for value in graph.objects(subject, predicate):
                if not isinstance(value, URIRef) or value in subjects:
                    continue
                scheme = urlsplit(str(value)).scheme.lower()
                if scheme not in {"http", "https"}:
                    raise ValueError(
                        f"unsafe linked IRI scheme {scheme!r} for {value}"
                    )


def _term_kind(graph: Graph, subject: URIRef) -> URIRef | None:
    """Return one supported RDF term kind, including entailed classes."""
    kinds = {kind for kind in _MAPPING_FOR_KIND if (subject, RDF.type, kind) in graph}
    if any(graph.objects(subject, RDFS.subClassOf)):
        kinds.add(OWL.Class)
    return next(iter(kinds)) if len(kinds) == 1 else None


def validate_compatibility_graph(
    canonical: Graph,
    compatibility: Graph,
) -> None:
    """Reject namespace mappings whose local name or RDF term kind differs."""
    mappings = {
        (subject, predicate, target)
        for predicate in set(_MAPPING_FOR_KIND.values())
        for subject, target in compatibility.subject_objects(predicate)
    }
    if not mappings:
        raise ValueError("namespace compatibility vocabulary has no mappings")
    for subject, predicate, target in mappings:
        canonical_iri, deprecated_iri = str(subject), str(target)
        if not canonical_iri.startswith(CANONICAL_NAMESPACE) or not deprecated_iri.startswith(
            DEPRECATED_NAMESPACE
        ):
            raise ValueError("namespace compatibility mapping has an unexpected namespace")
        if canonical_iri.removeprefix(CANONICAL_NAMESPACE) != deprecated_iri.removeprefix(
            DEPRECATED_NAMESPACE
        ):
            raise ValueError("namespace compatibility mapping has different local names")
        canonical_kind = _term_kind(canonical, subject)
        deprecated_kind = _term_kind(compatibility, target)
        if canonical_kind is None or canonical_kind != deprecated_kind:
            raise ValueError("namespace compatibility mapping has different term kinds")
        if _MAPPING_FOR_KIND[canonical_kind] != predicate:
            raise ValueError("namespace compatibility mapping uses the wrong predicate")


def validate_shapes_graph(shapes: Graph, canonical: Graph) -> None:
    """Reject SHACL shapes whose targets dangle outside the ontology.

    A shape that targets a class absent from the canonical graph, or
    constrains a path neither declared there nor an allowlisted RDF
    reification/PROV-O provenance predicate, would silently validate nothing
    -- the publication boundary refuses it instead (ADR 0207 decision 10).
    Only URI-valued targets and paths are checked; literal sh:path values
    are not part of this contract.
    """
    if not any(shapes.triples((None, RDF.type, SH.NodeShape))):
        raise ValueError("SHACL shapes graph declares no sh:NodeShape")
    for predicate in (SH.targetClass, SH.path):
        for value in shapes.objects(None, predicate):
            if (
                not isinstance(value, URIRef)
                or str(value).startswith(CANONICAL_NAMESPACE)
                or (predicate == SH.path and value in STANDARD_SHACL_PATHS)
            ):
                continue
            kind = "targetClass" if predicate == SH.targetClass else "path"
            raise ValueError(
                f"SHACL {kind} target outside the canonical namespace: {value}"
            )
    declared_classes = {
        subject
        for subject in canonical.subjects(RDF.type, OWL.Class)
        if isinstance(subject, URIRef)
    }
    # Entailed classes: anything with a subclass assertion is a class.
    declared_classes.update(
        subject
        for subject, _ in canonical.subject_objects(RDFS.subClassOf)
        if isinstance(subject, URIRef)
    )
    declared_properties = {
        subject
        for subject in canonical.subjects(RDF.type, OWL.ObjectProperty)
        if isinstance(subject, URIRef)
    }
    declared_properties.update(
        subject
        for subject in canonical.subjects(RDF.type, OWL.DatatypeProperty)
        if isinstance(subject, URIRef)
    )
    declared_properties.update(STANDARD_SHACL_PATHS)
    for target in shapes.objects(None, SH.targetClass):
        if target not in declared_classes:
            raise ValueError(f"SHACL targetClass is not an ontology class: {target}")
    for path in shapes.objects(None, SH.path):
        if path not in declared_properties:
            raise ValueError(f"SHACL property path is not an ontology property: {path}")


def _validate_output_directory(output_dir: Path, source: Path, profile: Path) -> Path:
    """Resolve an output path and ensure replacement cannot delete source data."""
    requested = output_dir.expanduser()
    if requested.is_symlink():
        raise ValueError("output directory must not be a symbolic link")
    output = requested.resolve()
    if source.is_relative_to(output) or profile.is_relative_to(output):
        raise ValueError("output directory overlaps ontology source files")
    if output.exists() and not (output / OUTPUT_MARKER).is_file():
        raise ValueError("refusing to replace an unmarked output directory")
    return output


def publish_site(repository_root: Path, output_dir: Path) -> None:
    """Validate sources and publish one safely replaceable static site tree."""
    root = repository_root.resolve()
    source = root / SOURCE_RELATIVE_PATH
    profile = root / PROV_PROFILE_RELATIVE_PATH
    compatibility_source = root / COMPATIBILITY_RELATIVE_PATH
    shapes_source = root / SHAPES_RELATIVE_PATH
    if not source.is_file():
        raise FileNotFoundError(f"ontology source is missing: {source}")
    if not profile.is_file():
        raise FileNotFoundError(f"PROV-O support profile is missing: {profile}")
    if not compatibility_source.is_file():
        raise FileNotFoundError(
            f"namespace compatibility vocabulary is missing: {compatibility_source}"
        )
    if not shapes_source.is_file():
        raise FileNotFoundError(f"SHACL shapes graph is missing: {shapes_source}")

    output = _validate_output_directory(output_dir, source, profile)
    renderer = _load_renderer(root)
    graph = Graph().parse(source, format="turtle")
    Graph().parse(profile, format="turtle")
    compatibility_graph = Graph().parse(compatibility_source, format="turtle")
    shapes_graph = Graph().parse(shapes_source, format="turtle")
    validate_public_graph(graph, renderer)
    validate_compatibility_graph(graph, compatibility_graph)
    validate_shapes_graph(shapes_graph, graph)

    if output.exists():
        shutil.rmtree(output)
    try:
        renderer.build_site(root, output)
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise
    (output / OUTPUT_MARKER).write_text("", encoding="utf-8")


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    """Parse repository and output paths for the publication command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="LineageWeave repository root",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_site"),
        help="Static site output directory",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    """Publish the site from CLI arguments and return a process exit code."""
    args = _parse_args(argv)
    publish_site(args.repository_root, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
