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
from rdflib.namespace import OWL, RDF, RDFS, SKOS

try:
    from scripts.ontology_site_contract import public_fragment
except ModuleNotFoundError:  # direct execution with ``scripts`` as sys.path[0]
    from ontology_site_contract import public_fragment

OUTPUT_MARKER = ".lineageweave-ontology-site"
SOURCE_RELATIVE_PATH = Path("docs/ontology/lineageweave-kg.ttl")
PROV_PROFILE_RELATIVE_PATH = Path("docs/ontology/prov-o-support-profile.ttl")
TERM_TYPES: tuple[URIRef, ...] = (
    OWL.Class,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    SKOS.ConceptScheme,
    SKOS.Concept,
)
LINK_PREDICATES: tuple[URIRef, ...] = (
    RDF.type,
    RDFS.subClassOf,
    RDFS.domain,
    RDFS.range,
    OWL.inverseOf,
    SKOS.broader,
    SKOS.narrower,
    SKOS.inScheme,
)


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


def _public_subjects(graph: Graph) -> set[URIRef]:
    """Return URI subjects included in the public HTML term inventory."""
    return {
        subject
        for term_type in TERM_TYPES
        for subject in graph.subjects(RDF.type, term_type)
        if isinstance(subject, URIRef)
    }


def validate_public_graph(graph: Graph) -> None:
    """Reject RDF structures that cannot be rendered safely and uniquely."""
    subjects = _public_subjects(graph)
    fragment_owner: dict[str, URIRef] = {}
    for subject in sorted(subjects, key=str):
        fragment = public_fragment(_fragment(subject))
        owner = fragment_owner.setdefault(fragment, subject)
        if owner != subject:
            raise ValueError(
                f"duplicate ontology fragment {fragment!r}: {owner} and {subject}"
            )

    for subject in subjects:
        for predicate in LINK_PREDICATES:
            for value in graph.objects(subject, predicate):
                if not isinstance(value, URIRef) or value in subjects:
                    continue
                scheme = urlsplit(str(value)).scheme.lower()
                if scheme not in {"http", "https"}:
                    raise ValueError(
                        f"unsafe linked IRI scheme {scheme!r} for {value}"
                    )


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
    if not source.is_file():
        raise FileNotFoundError(f"ontology source is missing: {source}")
    if not profile.is_file():
        raise FileNotFoundError(f"PROV-O support profile is missing: {profile}")

    output = _validate_output_directory(output_dir, source, profile)
    graph = Graph().parse(source, format="turtle")
    validate_public_graph(graph)

    renderer = _load_renderer(root)
    if output.exists():
        shutil.rmtree(output)
    renderer.build_site(root, output)
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
