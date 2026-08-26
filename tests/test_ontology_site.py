"""Contract tests for the deterministic LineageWeave ontology Pages site."""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
from urllib.parse import unquote

from rdflib import Graph
from rdflib.compare import isomorphic
from rdflib.plugins.parsers.jsonld import to_rdf

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_ontology_site.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_ontology_site", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("ontology site builder could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_supports_direct_script_import_context(monkeypatch) -> None:
    """The CLI fallback imports the sibling contract when not package-loaded."""
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    original_import = builtins.__import__

    def block_package_import(name, globals_=None, locals_=None, fromlist=(), level=0):
        if name == "scripts.ontology_site_contract":
            raise ModuleNotFoundError(name=name)
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", block_package_import)
    spec = importlib.util.spec_from_file_location("build_ontology_site_direct", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.public_fragment("Safety/한국어 term") == "Safety%2F%ED%95%9C%EA%B5%AD%EC%96%B4%20term"


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_build_publishes_dereferenceable_html_and_machine_formats(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"

    builder.build_site(ROOT, output)

    ontology_dir = output / "ontology"
    assert (output / ".nojekyll").is_file()
    assert (output / "index.html").is_file()
    assert (ontology_dir / "index.html").is_file()
    sources = (
        ROOT / "docs" / "ontology" / "lineageweave-kg.ttl",
        ROOT / "docs" / "ontology" / "soc-2018-structure.ttl",
    )
    assert (ontology_dir / "ontology.ttl").read_text(encoding="utf-8") == (
        "\n".join(path.read_text(encoding="utf-8").rstrip() for path in sources)
        + "\n"
    )
    assert (ontology_dir / "prov-o-support-profile.ttl").is_file()
    assert (ontology_dir / "namespace-compatibility.ttl").read_bytes() == (
        ROOT / "docs" / "ontology" / "namespace-compatibility.ttl"
    ).read_bytes()
    assert (ontology_dir / "lineageweave-kg-shapes.ttl").read_bytes() == (
        ROOT / "docs" / "ontology" / "lineageweave-kg-shapes.ttl"
    ).read_bytes()

    html = (ontology_dir / "index.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://contextualwisdomlab.github.io/LineageWeave/ontology">' in html
    assert "canonical metadata fetches no subresource" in html
    assert 'id="Post"' in html
    assert 'href="#Post"' in html
    assert "LineageWeave Knowledge Graph Ontology" in html
    assert "ontology.ttl" in html
    assert "ontology.jsonld" in html
    assert "ontology.nt" in html
    assert "lineageweave-kg-shapes.ttl" in html


def test_render_term_escapes_untrusted_ontology_text() -> None:
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#Unsafe")
    graph.add((term, builder.RDF.type, builder.OWL.Class))
    graph.add(
        (term, builder.RDFS.label, builder.Literal("<script>alert(1)</script>"))
    )
    graph.add(
        (term, builder.RDFS.comment, builder.Literal("A <source> & evidence."))
    )

    rendered = builder._render_term(graph, term, {term})

    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "A &lt;source&gt; &amp; evidence." in rendered


def test_render_term_omits_missing_lookup_code_and_does_not_link_external_iris() -> None:
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#Term")
    external = builder.URIRef("http://www.w3.org/2002/07/owl#Class")
    graph.add((term, builder.RDF.type, external))

    rendered = builder._render_term(graph, term, {term})

    assert "Lookup code" not in rendered
    assert f"<code>{external}</code>" in rendered
    assert f'href="{external}"' not in rendered


def test_preferred_literal_uses_english_before_untagged_and_other_languages() -> None:
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#Localized")
    graph.add((term, builder.RDFS.label, builder.Literal("untagged")))
    graph.add((term, builder.RDFS.label, builder.Literal("English", lang="en")))
    graph.add((term, builder.RDFS.label, builder.Literal("한국어", lang="ko")))

    assert builder._preferred_literal(graph, term, builder.RDFS.label) == "English"


def test_render_term_uses_skos_preferred_label_without_rdfs_label() -> None:
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#RawFragment")
    graph.add((term, builder.RDF.type, builder.SKOS.Concept))
    graph.add((term, builder.SKOS.prefLabel, builder.Literal("Human label", lang="en")))

    rendered = builder._render_term(graph, term, {term})

    assert "Human label</h3>" in rendered
    assert 'aria-label="Link to Human label"' in rendered


def test_render_term_exposes_worker_function_domain_and_rank() -> None:
    """Published worker functions show their defining FJA coordinates."""
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#Analyzing")
    graph.add((term, builder.RDF.type, builder.SKOS.Concept))
    graph.add((term, builder.CANONICAL_FJA_DOMAIN_PREDICATE, builder.Literal("data")))
    graph.add((term, builder.CANONICAL_FJA_RANK_PREDICATE, builder.Literal(2)))

    rendered = builder._render_term(graph, term, {term})

    assert "<dt>FJA domain</dt><dd><code>data</code></dd>" in rendered
    assert "<dt>FJA rank</dt><dd><code>2</code></dd>" in rendered


def test_render_term_href_decodes_to_its_html_id() -> None:
    builder = _load_builder()
    graph = Graph()
    raw_fragment = "Safety/한국어-term"
    term = builder.URIRef(f"https://example.test/ontology#{raw_fragment}")
    graph.add((term, builder.RDF.type, builder.OWL.Class))

    rendered = builder._render_term(graph, term, {term})
    fragment_href = builder.public_fragment(raw_fragment)

    assert f'id="{raw_fragment}"' in rendered
    assert f'href="#{fragment_href}"' in rendered
    assert unquote(fragment_href) == raw_fragment


def test_serializations_round_trip_to_the_source_graph(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build_site(ROOT, output)

    source = Graph().parse(
        ROOT / "docs" / "ontology" / "lineageweave-kg.ttl", format="turtle"
    )
    source.parse(
        ROOT / "docs" / "ontology" / "soc-2018-structure.ttl", format="turtle"
    )
    jsonld = Graph()
    to_rdf(json.loads((output / "ontology" / "ontology.jsonld").read_text()), jsonld)
    ntriples = Graph().parse(output / "ontology" / "ontology.nt", format="nt")
    compatibility_source = Graph().parse(
        ROOT / "docs" / "ontology" / "namespace-compatibility.ttl", format="turtle"
    )
    compatibility_published = Graph().parse(
        output / "ontology" / "namespace-compatibility.ttl", format="turtle"
    )

    assert isomorphic(source, jsonld)
    assert isomorphic(source, ntriples)
    assert isomorphic(compatibility_source, compatibility_published)


def test_build_is_byte_deterministic(tmp_path: Path) -> None:
    builder = _load_builder()
    first = tmp_path / "first"
    second = tmp_path / "second"

    builder.build_site(ROOT, first)
    builder.build_site(ROOT, second)

    assert _tree_hashes(first) == _tree_hashes(second)


def test_metadata_manifest_has_source_digest_and_no_build_clock(tmp_path: Path) -> None:
    builder = _load_builder()
    output = tmp_path / "site"
    builder.build_site(ROOT, output)

    manifest = json.loads((output / "ontology" / "manifest.json").read_text(encoding="utf-8"))
    source = ROOT / "docs" / "ontology" / "lineageweave-kg.ttl"
    assert manifest["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    fragment = ROOT / "docs" / "ontology" / "soc-2018-structure.ttl"
    assert manifest["source_tree_sha256"] == hashlib.sha256(
        source.read_bytes() + fragment.read_bytes()
    ).hexdigest()
    assert [entry["path"] for entry in manifest["source_files"]] == [
        "docs/ontology/lineageweave-kg.ttl",
        "docs/ontology/soc-2018-structure.ttl",
    ]
    assert "built_at" not in manifest
    assert manifest["documentation_url"] == "https://contextualwisdomlab.github.io/LineageWeave/ontology"
    assert manifest["generated_artifacts"] == [
        "index.html",
        "lineageweave-kg-shapes.ttl",
        "manifest.json",
        "namespace-compatibility.ttl",
        "ontology.jsonld",
        "ontology.nt",
        "ontology.ttl",
        "prov-o-support-profile.ttl",
    ]
    assert manifest["shapes_path"] == "docs/ontology/lineageweave-kg-shapes.ttl"


def test_helpers_cover_slash_fragments_json_lists_and_missing_ontology() -> None:
    builder = _load_builder()
    assert builder._fragment(builder.URIRef("https://example.test/vocabulary/Term")) == "Term"
    assert builder._canonicalize_json({"@list": ["b", "a"]}) == {"@list": ["b", "a"]}
    graph = Graph()
    graph.add(
        (
            builder.URIRef("https://example.test/ontology#Term"),
            builder.RDF.type,
            builder.OWL.Class,
        )
    )
    nav, sections, term_count = builder._render_term_sections(graph)
    assert 'href="#classes"' in nav
    assert 'id="object-properties"' not in sections
    assert term_count == 1
    try:
        builder._ontology_metadata(Graph())
    except ValueError as exc:
        assert "owl:Ontology" in str(exc)
    else:
        raise AssertionError("missing owl:Ontology declaration was accepted")


def test_render_term_sections_keeps_one_anchor_for_multi_typed_terms() -> None:
    builder = _load_builder()
    graph = Graph()
    term = builder.URIRef("https://example.test/ontology#SharedTerm")
    graph.add((term, builder.RDF.type, builder.OWL.Class))
    graph.add((term, builder.RDF.type, builder.SKOS.Concept))

    nav, sections, term_count = builder._render_term_sections(graph)

    assert nav.count("SharedTerm") == 0
    assert sections.count('id="SharedTerm"') == 1
    assert term_count == 1


def test_builder_fails_closed_for_missing_sources_and_rejects_existing_output(tmp_path: Path) -> None:
    builder = _load_builder()
    repository = tmp_path / "repository"
    output = tmp_path / "site"
    output.mkdir()
    (output / "stale.txt").write_text("stale", encoding="utf-8")

    try:
        builder.build_site(repository, output)
    except FileNotFoundError as exc:
        assert "ontology source" in str(exc)
    else:
        raise AssertionError("missing ontology source was accepted")

    ontology_dir = repository / "docs" / "ontology"
    ontology_dir.mkdir(parents=True)
    (ontology_dir / "lineageweave-kg.ttl").write_text(
        (ROOT / "docs" / "ontology" / "lineageweave-kg.ttl").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    try:
        builder.build_site(repository, output)
    except FileNotFoundError as exc:
        assert "PROV-O support profile" in str(exc)
    else:
        raise AssertionError("missing PROV-O profile was accepted")

    (ontology_dir / "prov-o-support-profile.ttl").write_text("", encoding="utf-8")

    try:
        builder.build_site(repository, output)
    except FileNotFoundError as exc:
        assert "namespace compatibility" in str(exc)
    else:
        raise AssertionError("missing namespace compatibility vocabulary was accepted")

    (ontology_dir / "namespace-compatibility.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "namespace-compatibility.ttl").read_bytes()
    )

    try:
        builder.build_site(repository, output)
    except FileNotFoundError as exc:
        assert "SHACL shapes graph" in str(exc)
    else:
        raise AssertionError("missing SHACL shapes graph was accepted")

    (ontology_dir / "lineageweave-kg-shapes.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "lineageweave-kg-shapes.ttl").read_bytes()
    )

    try:
        builder.build_site(repository, output)
    except FileNotFoundError as exc:
        assert "ontology source fragment" in str(exc)
    else:
        raise AssertionError("missing ontology source fragment was accepted")

    (ontology_dir / "soc-2018-structure.ttl").write_bytes(
        (ROOT / "docs" / "ontology" / "soc-2018-structure.ttl").read_bytes()
    )

    try:
        builder.build_site(repository, output)
    except FileExistsError as exc:
        assert "publish_ontology_site" in str(exc)
    else:
        raise AssertionError("direct builder replaced an existing output")
    assert (output / "stale.txt").is_file()
    shutil.rmtree(output)
    builder.build_site(repository, output)
    assert (output / "ontology" / "index.html").is_file()


def test_cli_main_and_module_entrypoint(tmp_path: Path, monkeypatch) -> None:
    builder = _load_builder()
    output = tmp_path / "direct"
    assert builder.main(["--repository-root", str(ROOT), "--output-dir", str(output)]) == 0
    assert (output / "ontology" / "index.html").is_file()

    import runpy
    import sys

    entry_output = tmp_path / "entry"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--repository-root",
            str(ROOT),
            "--output-dir",
            str(entry_output),
        ],
    )
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("module entrypoint did not exit")
    assert (entry_output / "ontology" / "manifest.json").is_file()
