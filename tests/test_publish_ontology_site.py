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

    def block_package_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "scripts.ontology_site_contract":
            raise ModuleNotFoundError(name=name)
        return original_import(name, globals, locals, fromlist, level)

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
    for name in ("lineageweave-kg.ttl", "prov-o-support-profile.ttl"):
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
    duplicate = Graph()
    first = URIRef("https://one.example/ontology#Shared")
    second = URIRef("https://two.example/ontology#Shared")
    duplicate.add((first, RDF.type, OWL.Class))
    duplicate.add((second, RDF.type, OWL.Class))

    with pytest.raises(ValueError, match="duplicate ontology fragment"):
        publisher.validate_public_graph(duplicate)

    unsafe = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    unsafe.add((subject, RDF.type, OWL.Class))
    unsafe.add((subject, RDFS.subClassOf, URIRef("javascript:alert(1)")))
    with pytest.raises(ValueError, match="unsafe linked IRI scheme"):
        publisher.validate_public_graph(unsafe)


def test_graph_validation_allows_http_relations_and_multiple_term_types() -> None:
    publisher = _load_publisher()
    graph = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    graph.add((subject, RDF.type, OWL.Class))
    graph.add((subject, RDF.type, OWL.AnnotationProperty))
    graph.add((subject, RDFS.subClassOf, URIRef("https://external.example/Parent")))

    publisher.validate_public_graph(graph)


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
    from rdflib import BNode, Literal

    graph = Graph()
    subject = URIRef("https://example.test/ontology#Subject")
    local_parent = URIRef("https://example.test/ontology#Parent")
    graph.add((subject, RDF.type, OWL.Class))
    graph.add((local_parent, RDF.type, OWL.Class))
    graph.add((BNode(), RDF.type, OWL.Class))
    graph.add((subject, RDFS.subClassOf, local_parent))
    graph.add((subject, RDFS.domain, Literal("not a link")))

    publisher.validate_public_graph(graph)


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
