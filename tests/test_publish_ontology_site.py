"""Security and deployment-boundary tests for ontology Pages publication."""

from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_ontology_site.py"


def _load_publisher():
    spec = importlib.util.spec_from_file_location("publish_ontology_site", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("ontology publisher could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publisher_supports_direct_script_import_context(monkeypatch) -> None:
    """The CLI fallback imports the sibling contract when not package-loaded."""
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    original_import = builtins.__import__

    def block_package_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        if name == "scripts.ontology_site_contract":
            raise ModuleNotFoundError(name=name)
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", block_package_import)
    spec = importlib.util.spec_from_file_location("publish_ontology_site_direct", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.public_fragment("Safety/한국어 term") == "Safety%2F%ED%95%9C%EA%B5%AD%EC%96%B4%20term"


def _repository_fixture(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    ontology_dir = repository / "docs" / "ontology"
    scripts_dir = repository / "scripts"
    ontology_dir.mkdir(parents=True)
    scripts_dir.mkdir(parents=True)
    for name in (
        "lineageweave-kg.ttl",
        "prov-o-support-profile.ttl",
        "namespace-compatibility.ttl",
        "lineageweave-kg-shapes.ttl",
    ):
        (ontology_dir / name).write_bytes((ROOT / "docs" / "ontology" / name).read_bytes())
    (scripts_dir / "build_ontology_site.py").write_bytes(
        (ROOT / "scripts" / "build_ontology_site.py").read_bytes()
    )
    (scripts_dir / "ontology_site_contract.py").write_bytes(
        (ROOT / "scripts" / "ontology_site_contract.py").read_bytes()
    )
    return repository


def test_publication_refuses_unmarked_existing_output(tmp_path: Path) -> None:
    publisher = _load_publisher()
    repository = _repository_fixture(tmp_path)
    output = tmp_path / "site"
    output.mkdir()
    (output / "unrelated.txt").write_text("do not delete", encoding="utf-8")

    with pytest.raises(ValueError, match="unmarked"):
        publisher.publish_site(repository, output)

    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "do not delete"


def test_publication_replaces_only_marked_output_and_writes_marker(tmp_path: Path) -> None:
    publisher = _load_publisher()
    repository = _repository_fixture(tmp_path)
    output = tmp_path / "site"

    publisher.publish_site(repository, output)
    (output / "stale.txt").write_text("stale", encoding="utf-8")
    publisher.publish_site(repository, output)

    assert (output / publisher.OUTPUT_MARKER).is_file()
    assert not (output / "stale.txt").exists()
    assert (output / "ontology" / "index.html").is_file()


def test_publication_removes_partial_output_when_build_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    publisher = _load_publisher()
    repository = _repository_fixture(tmp_path)
    output = tmp_path / "site"
    renderer = publisher._load_renderer(repository)

    def fail_build(_root: Path, output_dir: Path) -> None:
        output_dir.mkdir()
        (output_dir / "partial.txt").write_text("partial", encoding="utf-8")
        raise RuntimeError("build failed")

    monkeypatch.setattr(renderer, "build_site", fail_build)
    monkeypatch.setattr(publisher, "_load_renderer", lambda _root: renderer)

    with pytest.raises(RuntimeError, match="build failed"):
        publisher.publish_site(repository, output)

    assert not output.exists()


def test_publication_rejects_symlink_and_source_overlapping_outputs(tmp_path: Path) -> None:
    publisher = _load_publisher()
    repository = _repository_fixture(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    symlink = tmp_path / "site-link"
    symlink.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        publisher.publish_site(repository, symlink)
    with pytest.raises(ValueError, match="overlaps"):
        publisher.publish_site(repository, repository)


def test_graph_validation_rejects_duplicate_fragments_and_unsafe_links() -> None:
    publisher = _load_publisher()
    renderer = publisher._load_renderer(ROOT)
    duplicate = Graph()
    first = URIRef("https://one.example/ontology#Shared")
    second = URIRef("https://two.example/ontology#Shared")
    duplicate.add((first, RDF.type, OWL.Class))
    duplicate.add((second, RDF.type, OWL.Class))

    with pytest.raises(ValueError, match="duplicate ontology fragment"):
        publisher.validate_public_graph(duplicate, renderer)

    unsafe = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    unsafe.add((subject, RDF.type, OWL.Class))
    unsafe.add((subject, RDFS.subClassOf, URIRef("javascript:alert(1)")))
    with pytest.raises(ValueError, match="unsafe linked IRI scheme"):
        publisher.validate_public_graph(unsafe, renderer)


def test_graph_validation_allows_http_relations_and_multiple_term_types() -> None:
    publisher = _load_publisher()
    renderer = publisher._load_renderer(ROOT)
    graph = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    graph.add((subject, RDF.type, OWL.Class))
    graph.add((subject, RDF.type, OWL.AnnotationProperty))
    graph.add((subject, RDFS.subClassOf, URIRef("https://external.example/Parent")))

    publisher.validate_public_graph(graph, renderer)


def test_compatibility_validation_is_term_kind_safe() -> None:
    publisher = _load_publisher()
    canonical = Graph().parse(
        ROOT / "docs" / "ontology" / "lineageweave-kg.ttl", format="turtle"
    )
    compatibility = Graph().parse(
        ROOT / "docs" / "ontology" / "namespace-compatibility.ttl", format="turtle"
    )

    publisher.validate_compatibility_graph(canonical, compatibility)

    post = URIRef(f"{publisher.CANONICAL_NAMESPACE}Post")
    legacy_post = URIRef(f"{publisher.DEPRECATED_NAMESPACE}Post")
    for broken, message in (
        (Graph(), "no mappings"),
        (
            Graph().add((post, OWL.equivalentClass, URIRef("https://other.test/#Post"))),
            "unexpected namespace",
        ),
        (
            Graph().add(
                (
                    post,
                    OWL.equivalentClass,
                    URIRef(f"{publisher.DEPRECATED_NAMESPACE}Person"),
                )
            ),
            "different local names",
        ),
    ):
        with pytest.raises(ValueError, match=message):
            publisher.validate_compatibility_graph(canonical, broken)

    wrong_kind = Graph().add((post, RDF.type, OWL.ObjectProperty))
    with pytest.raises(ValueError, match="different term kinds"):
        publisher.validate_compatibility_graph(wrong_kind, compatibility)

    wrong_predicate = Graph()
    wrong_predicate.add((legacy_post, RDF.type, OWL.Class))
    wrong_predicate.add((post, OWL.equivalentProperty, legacy_post))
    with pytest.raises(ValueError, match="wrong predicate"):
        publisher.validate_compatibility_graph(canonical, wrong_predicate)

    ambiguous = Graph()
    ambiguous.add((post, RDF.type, OWL.Class))
    ambiguous.add((post, RDF.type, OWL.ObjectProperty))
    assert publisher._term_kind(ambiguous, post) is None


def test_shapes_validation_rejects_dangling_targets_and_outside_namespace() -> None:
    """ADR 0205 decision 10: a shape targeting an undeclared class or
    path validates nothing silently, so publication refuses it; only
    canonical-namespace targets are allowed.
    """
    from rdflib.namespace import SH

    publisher = _load_publisher()
    canonical = Graph().parse(
        ROOT / "docs" / "ontology" / "lineageweave-kg.ttl", format="turtle"
    )

    with pytest.raises(ValueError, match="declares no sh:NodeShape"):
        publisher.validate_shapes_graph(Graph(), canonical)

    outside_target = Graph()
    outside_target.add((URIRef(f"{publisher.CANONICAL_NAMESPACE}PostShape"), RDF.type, SH.NodeShape))
    outside_target.add(
        (
            URIRef(f"{publisher.CANONICAL_NAMESPACE}PostShape"),
            SH.targetClass,
            URIRef("https://example.test/ontology#Ghost"),
        )
    )
    with pytest.raises(ValueError, match="outside the canonical namespace"):
        publisher.validate_shapes_graph(outside_target, canonical)

    dangling_class = Graph()
    dangling_class.add((URIRef(f"{publisher.CANONICAL_NAMESPACE}S"), RDF.type, SH.NodeShape))
    dangling_class.add(
        (
            URIRef(f"{publisher.CANONICAL_NAMESPACE}S"),
            SH.targetClass,
            URIRef(f"{publisher.CANONICAL_NAMESPACE}NotAClass"),
        )
    )
    with pytest.raises(ValueError, match="not an ontology class"):
        publisher.validate_shapes_graph(dangling_class, canonical)

    dangling_path = Graph()
    shape = URIRef(f"{publisher.CANONICAL_NAMESPACE}PostShape")
    dangling_path.add((shape, RDF.type, SH.NodeShape))
    dangling_path.add((shape, SH.targetClass, URIRef(f"{publisher.CANONICAL_NAMESPACE}Post")))
    dangling_path.add((shape, SH.path, URIRef(f"{publisher.CANONICAL_NAMESPACE}ghostColumn")))
    with pytest.raises(ValueError, match="not an ontology term"):
        publisher.validate_shapes_graph(dangling_path, canonical)

    publisher.validate_shapes_graph(
        Graph().parse(ROOT / "docs" / "ontology" / "lineageweave-kg-shapes.ttl", format="turtle"),
        canonical,
    )


def test_main_publishes_site(tmp_path: Path) -> None:
    publisher = _load_publisher()
    repository = _repository_fixture(tmp_path)
    output = tmp_path / "site"

    assert publisher.main([
        "--repository-root",
        str(repository),
        "--output-dir",
        str(output),
    ]) == 0
    assert (output / "ontology" / "manifest.json").is_file()


def test_loader_and_fragment_failure_branches(tmp_path: Path, monkeypatch) -> None:
    publisher = _load_publisher()
    assert publisher._fragment(URIRef("https://example.test/vocabulary/Term")) == "Term"
    monkeypatch.setattr(publisher.importlib.util, "spec_from_file_location", lambda *_args: None)
    with pytest.raises(RuntimeError, match="could not be loaded"):
        publisher._load_renderer(tmp_path)


def test_graph_validation_ignores_non_uri_and_local_link_objects() -> None:
    publisher = _load_publisher()
    renderer = publisher._load_renderer(ROOT)
    from rdflib import BNode, Literal

    graph = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    local_parent = URIRef("https://example.test/ontology#Parent")
    graph.add((subject, RDF.type, OWL.Class))
    graph.add((local_parent, RDF.type, OWL.Class))
    graph.add((BNode(), RDF.type, OWL.Class))
    graph.add((subject, RDFS.subClassOf, local_parent))
    graph.add((subject, RDFS.domain, Literal("not a link")))

    publisher.validate_public_graph(graph, renderer)


def test_publication_fails_closed_for_missing_sources(tmp_path: Path) -> None:
    publisher = _load_publisher()
    repository = tmp_path / "repository"
    output = tmp_path / "site"

    with pytest.raises(FileNotFoundError, match="ontology source"):
        publisher.publish_site(repository, output)

    ontology_dir = repository / "docs" / "ontology"
    ontology_dir.mkdir(parents=True)
    (ontology_dir / "lineageweave-kg.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "lineageweave-kg.ttl").read_bytes()
    )
    with pytest.raises(FileNotFoundError, match="PROV-O support profile"):
        publisher.publish_site(repository, output)

    (ontology_dir / "prov-o-support-profile.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "prov-o-support-profile.ttl").read_bytes()
    )
    with pytest.raises(FileNotFoundError, match="namespace compatibility"):
        publisher.publish_site(repository, output)

    (ontology_dir / "namespace-compatibility.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "namespace-compatibility.ttl").read_bytes()
    )
    with pytest.raises(FileNotFoundError, match="SHACL shapes graph"):
        publisher.publish_site(repository, output)


def test_module_entrypoint(tmp_path: Path, monkeypatch) -> None:
    import runpy
    import sys

    repository = _repository_fixture(tmp_path)
    output = tmp_path / "entry-site"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--repository-root",
            str(repository),
            "--output-dir",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc_info.value.code == 0
    assert (output / "ontology" / "index.html").is_file()
